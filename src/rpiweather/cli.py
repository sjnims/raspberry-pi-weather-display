from __future__ import annotations

# ── standard library ─────────────────────────────────────────────────────────
import logging
import sys
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional
from zoneinfo import ZoneInfo

# ── third‑party ──────────────────────────────────────────────────────────────
import typer
import yaml
from pydantic import ValidationError

# ── rpiweather packages ──────────────────────────────────────────────────────
from rpiweather.config import WeatherConfig, load_config
from rpiweather.display.epaper import display_png
from rpiweather.display.error_ui import render_error_screen
from rpiweather.display.render import (
    FULL_REFRESH_INTERVAL,
    TEMPLATE,
    html_to_png,
)
from rpiweather.weather.api import (
    WeatherAPIError,
    build_context,
    fetch_weather,
)
from rpiweather.weather.helpers import (
    load_icon_mapping,
    get_battery_status,
    PiJuiceLike,
)
from rpiweather.helpers import (
    in_quiet_hours,
    seconds_until_quiet_end,
    get_refresh_delay_minutes,
    should_power_off,
)
from rpiweather.remote import should_stay_awake
from rpiweather.power import graceful_shutdown, schedule_wakeup

# ── CLI setup ────────────────────────────────────────────────────────────────
app = typer.Typer(help="E-Ink Weather Display CLI", add_completion=False)
config_app = typer.Typer(help="Config helpers")
app.add_typer(config_app, name="config")

logger: logging.Logger = logging.getLogger("rpiweather")

DEFAULT_STAY_AWAKE_URL = "http://localhost:8000/stay_awake.json"
MIN_SHUTDOWN_SLEEP_MIN = 20  # don’t power‑off for very short sleeps


# ───────────────────────── helper functions ─────────────────────────────────
def get_pijuice() -> Optional[PiJuiceLike]:
    try:
        import pijuice  # type: ignore[import-not-found]

        return pijuice.PiJuice(1, 0x14)  # type: ignore[call-arg]
    except Exception:
        return None


def get_soc(pijuice: Optional[PiJuiceLike]) -> int:
    if pijuice is None:
        return 100
    try:
        return pijuice.status.GetChargeLevel()["data"]  # type: ignore[attr-defined]
    except Exception:
        return 100


def ensure_rtc_synced(pijuice: Optional[PiJuiceLike]) -> None:
    if pijuice is None:
        return
    try:
        rtc_time = pijuice.rtc.GetTime()["data"]  # type: ignore[attr-defined]
        if rtc_time["year"] < 2024:
            pijuice.rtc.SetTime()  # type: ignore[attr-defined]
            logger.info("RTC set from system clock")
    except Exception as exc:
        logger.debug("RTC sync skipped: %s", exc)


# ───────────────────────── dashboard cycle ──────────────────────────────────
def cycle(
    cfg_obj: WeatherConfig,
    preview: bool,
    full_refresh: bool,
    soc: int,
    is_charging: bool,
    battery_warning: bool,
) -> bool:
    try:
        weather = fetch_weather(cfg_obj)
    except WeatherAPIError as err:
        logger.error("OpenWeather error (%s): %s", err.code, err.message)
        if not preview:
            with tempfile.TemporaryDirectory() as td:
                error_png = Path(td) / "error.png"
                render_error_screen(
                    f"API Error ({err.code}): {err.message}",
                    soc,
                    is_charging,
                    html_to_png_func=html_to_png,
                    out_path=error_png,
                )
        return False

    local_tz = ZoneInfo(cfg_obj.timezone)
    time_fmt = cfg_obj.time_format_general

    for d in weather.daily:
        d.sunrise_local = d.sunrise.astimezone(local_tz).strftime(time_fmt)
        d.sunset_local = d.sunset.astimezone(local_tz).strftime(time_fmt)

    weather.current.sunrise_local = weather.current.sunrise.astimezone(
        local_tz
    ).strftime(time_fmt)
    weather.current.sunset_local = weather.current.sunset.astimezone(local_tz).strftime(
        time_fmt
    )

    # Provide a strictly-typed url_for for templates
    def url_for(endpoint: str, filename: str = "") -> str:
        if endpoint == "static":
            return f"/static/{filename}"
        raise ValueError(f"Unsupported endpoint: {endpoint}")

    ctx: Dict[str, Any] = build_context(cfg_obj, weather)
    ctx["battery_soc"] = soc
    ctx["is_charging"] = is_charging
    ctx["battery_warning"] = battery_warning
    ctx["url_for"] = url_for

    html = TEMPLATE.render(**ctx)  # type: ignore
    out_dir = Path("preview")
    out_dir.mkdir(parents=True, exist_ok=True)

    html_path = out_dir / "dash-preview.html"
    png_path = out_dir / "dash.png"

    html_path.write_text(html, encoding="utf-8")
    html_to_png(html, png_path, preview=preview)

    if not preview:
        display_png(png_path, mode_override=0 if full_refresh else 2)
    return True


# ───────────────────────── main command ─────────────────────────────────────
@app.command()
def run(
    config: Path = typer.Option(..., "--config", "-c", exists=True, dir_okay=False),
    preview: bool = typer.Option(False, "--preview", "-p"),
    once: bool = typer.Option(False, "--once", "-1", help="Run one cycle then exit"),
    debug: bool = typer.Option(False, "--debug"),
    stay_awake_url: Optional[str] = typer.Option(
        None,
        help="Override URL that returns {'awake': true|false}. "
        "If omitted, value from config.yaml or the default URL is used.",
    ),
) -> None:
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    cfg_obj: WeatherConfig = load_config(config)
    load_icon_mapping()

    # precedence: CLI flag ▸ YAML ▸ default
    effective_url = stay_awake_url or cfg_obj.stay_awake_url or DEFAULT_STAY_AWAKE_URL

    base_minutes = cfg_obj.refresh_minutes

    pijuice = get_pijuice()
    ensure_rtc_synced(pijuice)

    error_streak = 0
    last_full_refresh = datetime.now()

    while True:
        now = datetime.now()
        # remote override
        if should_stay_awake(effective_url):
            logger.debug("Stay-awake flag true - overriding quiet hours")
            in_quiet = False
        else:
            in_quiet = in_quiet_hours(now, cfg_obj.quiet_hours)

        if in_quiet:
            secs = seconds_until_quiet_end(now, cfg_obj.quiet_hours)
            logger.info(
                "Quiet hours active → sleeping %d min until %s",
                secs // 60,
                (now + timedelta(seconds=secs)).strftime("%H:%M"),
            )
            time.sleep(secs)
            continue

        full_refresh = datetime.now() - last_full_refresh > FULL_REFRESH_INTERVAL
        soc = get_soc(pijuice)
        is_charging: bool = False
        battery_warning = False
        if pijuice:
            batt = get_battery_status(pijuice)
            is_charging = batt["is_charging"]
            battery_warning = batt["battery_warning"]

        ok = cycle(cfg_obj, preview, full_refresh, soc, is_charging, battery_warning)
        if ok:
            error_streak = 0
            if full_refresh:
                last_full_refresh = datetime.now()
        else:
            error_streak += 1
            if error_streak >= 3:
                logger.warning("3 consecutive failures → backing off x4 interval")
                time.sleep(base_minutes * 4 * 60)
                continue

        if once:
            break

        sleep_min = get_refresh_delay_minutes(base_minutes, soc)
        # decide whether to power off instead of sleep
        if should_power_off(cfg_obj, soc, now):
            wake_dt = datetime.now() + timedelta(minutes=sleep_min)
            schedule_wakeup(wake_dt)
            logger.info(
                "Powering off for %d min (SOC %d%%) → wake at %s",
                sleep_min,
                soc,
                wake_dt.strftime("%H:%M"),
            )
            graceful_shutdown()
            break

        logger.info(
            "Battery %02d%% → sleeping %d min (%.1fx normal)",
            soc,
            sleep_min,
            sleep_min / base_minutes,
        )
        time.sleep(sleep_min * 60)


# ───────────────────────── config sub‑commands ───────────────────────────────
@config_app.command("validate")
def validate_config(file: Path):
    """Validate a YAML config file against the schema."""
    try:
        load_config(file)
        typer.echo("✅ Config valid")
    except RuntimeError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc


@config_app.command("wizard")
def wizard(dst: Path = typer.Argument(..., help="Output config.yaml")):
    """Interactive prompt to create a config file."""
    typer.echo("Interactive config builder - press Enter for defaults.")

    while True:
        data: Dict[str, Any] = {
            "lat": float(typer.prompt("Latitude")),
            "lon": float(typer.prompt("Longitude")),
            "city": typer.prompt("City name"),
            "api_key": typer.prompt("OpenWeather API key", hide_input=True),
            "units": typer.prompt("Units [imperial|metric]", default="imperial"),
        }
        try:
            cfg = WeatherConfig(**data)
            break  # valid → exit loop
        except ValidationError as err:
            typer.secho("\nConfig error(s):", fg=typer.colors.RED, err=True)
            for e in err.errors():
                typer.secho(
                    f"  • {e['loc'][0]} - {e['msg']}", fg=typer.colors.RED, err=True
                )
            typer.echo("Please re-enter the values.\n")

    dst.write_text(yaml.safe_dump(cfg.model_dump(), sort_keys=False), encoding="utf-8")
    typer.secho(f"Config written to {dst}", fg=typer.colors.GREEN)


# ───────────────────────── module entrypoint ────────────────────────────────
if __name__ == "__main__":
    try:
        app()
    except KeyboardInterrupt:
        sys.exit(0)
