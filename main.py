# File: main.py  (circuit breaker, daily full refresh, RTC set, adaptive sleep)
from __future__ import annotations

import argparse
import logging
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
import webbrowser
import zoneinfo
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Protocol, TypedDict, Any, cast

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape, Template

from weather.api import WeatherAPIError, build_context, fetch_weather
from weather.helpers import deg_to_cardinal, moon_phase_icon, owm_icon_class
from display import display_png, render_error_screen

# ─────────────────────────── constants ───────────────────────────────────────

FULL_REFRESH_INTERVAL = timedelta(hours=24)
PROJECT_DIR = Path(__file__).resolve().parent

# ─────────────────────────── typing helpers ──────────────────────────────────


class PiJuiceLike(Protocol):
    """Subset of the PiJuice public API used by this program."""

    def GetChargeLevel(self) -> Dict[str, int]: ...
    def GetTime(self) -> Dict[str, Dict[str, int]]: ...
    def SetTime(self, time_dict: Dict[str, int]) -> Dict[str, int]: ...


class WeatherCfg(TypedDict):
    api_key: str
    latitude: float
    longitude: float
    units: str
    refresh_minutes: int


# ─────────────────────────── helpers ─────────────────────────────────────────


def load_config(path: Path) -> WeatherCfg:
    with path.open() as f:
        return yaml.safe_load(f)


def get_pijuice() -> Optional[PiJuiceLike]:
    """Return a PiJuice instance if the library is importable, else None."""
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
    """Set PiJuice RTC once per boot if it's uninitialised."""
    if pijuice is None:
        return
    try:
        rtc_time = pijuice.rtc.GetTime()["data"]  # type: ignore[attr-defined]
        if rtc_time["year"] < 2024:
            pijuice.rtc.SetTime()  # type: ignore[attr-defined]
            logger.info("RTC set from system clock")
    except Exception as exc:
        logger.debug("RTC sync skipped: %s", exc)


def calculate_sleep_minutes(base_minutes: int, soc: int) -> int:
    """
    Calculate sleep duration with progressive slowdown based on battery level.

    Parameters
    ----------
    base_minutes : int
        The base refresh interval from config.
    soc : int
        Battery State of Charge percentage (0-100).

    Returns
    -------
    int
        Sleep duration in minutes, progressively longer as battery depletes.
    """
    if soc <= 5:
        multiplier = 4.0  # Critical battery: 4x longer refresh
    elif soc <= 15:
        multiplier = 3.0  # Very low battery: 3x longer refresh
    elif soc <= 25:
        multiplier = 2.0  # Low battery: 2x longer refresh
    elif soc <= 50:
        multiplier = 1.5  # Medium battery: 1.5x longer refresh
    else:
        multiplier = 1.0  # High battery: normal refresh

    return int(base_minutes * multiplier)


def wind_rotation(deg: float, direction: str = "towards") -> float:
    """
    Calculate adjusted wind direction angle.

    Args:
        deg: Wind direction in degrees (0-360)
        direction: Either "towards" (default) or any other value for "from" direction

    Returns:
        Adjusted angle in degrees
    """
    return deg if direction == "towards" else (deg + 180) % 360


def html_to_png(html: str, out: Path, preview: bool = False) -> None:
    """
    Render `html` to `out` PNG.
    • macOS/Windows in --preview mode:
        - create a temp dir
        - copy project/static → temp/static
        - rewrite <link href="/static/..."> → <link href="static/...">
        - open the HTML in the default browser
    • Linux (or non-preview) path unchanged: use wkhtmltoimage
    """
    if preview and platform.system() != "Linux":
        tmpdir = Path(tempfile.mkdtemp())
        # copy static assets next to the html file
        shutil.copytree(PROJECT_DIR / "static", tmpdir / "static", dirs_exist_ok=True)
        html_path = tmpdir / "dash-preview.html"
        # make the CSS links relative
        html_local = re.sub(r'href="/static/', 'href="static/', html)
        html_path.write_text(html_local, "utf-8")
        webbrowser.open(html_path.as_uri())
        return

    # ---------- Pi / Linux PNG path ----------
    html_path = out.with_suffix(".html")
    html_path.write_text(html, "utf-8")

    cmd = [
        "wkhtmltoimage",
        "--width",
        "1872",
        "--height",
        "1404",
        html_path.as_posix(),
        out.as_posix(),
    ]
    if platform.system() == "Linux":
        cmd = ["xvfb-run", "-a"] + cmd

    subprocess.run(cmd, check=True)


# ─────────────────────────── environment setup ───────────────────────────────

logger: logging.Logger = logging.getLogger("weather_display")
LOCAL_TZ = zoneinfo.ZoneInfo("America/New_York")

ENV = Environment(
    loader=FileSystemLoader(PROJECT_DIR / "templates"),
    autoescape=select_autoescape(["html"]),
)
ENV.filters.update(
    {
        "deg_to_cardinal": deg_to_cardinal,
        "owm_icon": owm_icon_class,
        "moon_phase_icon": moon_phase_icon,
        "wind_rotation": wind_rotation,
    }
)


def ts_to_local(ts: int) -> datetime:
    return datetime.fromtimestamp(ts, tz=LOCAL_TZ)


def dt_format(d: datetime, fmt: str = "%H") -> str:
    return d.strftime(fmt)


ENV.filters["ts_to_dt"] = ts_to_local
ENV.filters["strftime"] = dt_format

TEMPLATE: Template = ENV.get_template("dashboard.html.j2")

# ─────────────────────────── main cycle ───────────────────────────────────────


def cycle(
    cfg: WeatherCfg,
    preview: bool,
    full_refresh: bool,
    soc: int,
    is_charging: bool,
) -> bool:
    """Render one dashboard update. Return False on API error (for circuit breaker)."""
    try:
        weather = fetch_weather(cfg)  # type: ignore[arg-type]
    except WeatherAPIError as err:
        logger.error("OpenWeather error (%s): %s", err.code, err.message)

        if not preview:  # Only show error on actual device, not in preview mode
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

    ctx: Dict[str, Any] = build_context(cast(Dict[str, Any], cfg), weather)
    ctx["battery_soc"] = soc
    ctx["is_charging"] = is_charging

    html = TEMPLATE.render(**ctx)  # type: ignore

    with tempfile.TemporaryDirectory() as td:
        png = Path(td) / "dash.png"
        html_to_png(html, png, preview=preview)

        if not preview:  # Pi / production path
            # mode 0 = full white‑black‑white, mode 2 = GC16 partial
            display_png(png, mode_override=0 if full_refresh else 2)
    return True


# ─────────────────────────── entrypoint ───────────────────────────────────────


def main() -> None:
    ap = argparse.ArgumentParser(description="E-Ink Weather Display")
    ap.add_argument("--config", type=Path, required=True)
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    cfg: WeatherCfg = load_config(args.config)  # type: ignore[assignment]
    base_minutes = cfg.get("refresh_minutes", 120)

    pijuice = get_pijuice()
    ensure_rtc_synced(pijuice)

    error_streak = 0
    last_full_refresh = datetime.now()

    while True:
        full_refresh = datetime.now() - last_full_refresh > FULL_REFRESH_INTERVAL
        soc = get_soc(pijuice)
        is_charging: bool = False
        if pijuice:
            try:
                stat = pijuice.status.GetStatus()["data"]  # type: ignore[attr-defined]
                is_charging = stat.get("powerInput") == "GOOD"  # type: ignore[attr-defined]
            except Exception:
                pass
        ok = cycle(
            cfg,
            preview=args.preview,
            full_refresh=full_refresh,
            soc=soc,
            is_charging=is_charging,  # type: ignore[arg-type]
        )
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

        if args.once:
            break

        sleep_min = calculate_sleep_minutes(base_minutes, soc)
        logger.info(
            "Battery %02d%% → sleeping %d min (%.1fx normal)",
            soc,
            sleep_min,
            sleep_min / base_minutes,
        )
        time.sleep(sleep_min * 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
