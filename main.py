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
from datetime import datetime, timedelta
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

from weather.api import WeatherAPIError, build_context, fetch_weather
from weather.helpers import deg_to_cardinal, owm_icon_class
from display.epaper import display_png

logger = logging.getLogger("weather_display")

PROJECT_DIR = Path(__file__).resolve().parent
ENV = Environment(
    loader=FileSystemLoader(PROJECT_DIR / "templates"),
    autoescape=select_autoescape(["html"]),
)
ENV.filters.update(
    {
        "deg_to_cardinal": deg_to_cardinal,
        "owm_icon": owm_icon_class,
    }
)
ENV.filters["datetime"] = lambda ts: datetime.fromtimestamp(ts)
ENV.filters["strftime"] = lambda d, fmt: d.strftime(fmt)
TEMPLATE = ENV.get_template("dashboard.html")

# ─────────────────────────── helpers ──────────────────────────────────────────


def load_config(path: Path) -> dict:
    with path.open() as f:
        return yaml.safe_load(f)


def get_pijuice():
    try:
        import pijuice  # type: ignore

        return pijuice.PiJuice(1, 0x14)
    except Exception:
        return None


def get_soc(pijuice) -> int:
    if pijuice is None:
        return 100
    try:
        return pijuice.status.GetChargeLevel()["data"]
    except Exception:
        return 100


def ensure_rtc_synced(pijuice):
    """Set PiJuice RTC once per boot if it’s uninitialised."""
    if pijuice is None:
        return
    try:
        rtc_time = pijuice.rtc.GetTime()["data"]
        if rtc_time["year"] < 2024:
            pijuice.rtc.SetTime()
            logger.info("RTC set from system clock")
    except Exception as exc:
        logger.debug("RTC sync skipped: %s", exc)


# ─────────────────────────── main cycle ───────────────────────────────────────

FULL_REFRESH_INTERVAL = timedelta(hours=24)


def html_to_png(html: str, out: Path, preview: bool = False) -> None:
    """
    Render `html` to `out` PNG.
    • macOS/Windows in --preview mode:
        - create a temp dir
        - copy project/static → temp/static
        - rewrite <link href="/static/..."> → <link href="static/...">
        - open the HTML in the default browser
    • Linux (or non‑preview) path unchanged: use wkhtmltoimage
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


def cycle(
    cfg: dict, preview: bool, full_refresh: bool, soc: int, is_charging: bool
) -> bool:
    """Render one dashboard update. Return False on API error (for circuit breaker)."""
    try:
        weather = fetch_weather(cfg)
    except WeatherAPIError as err:
        logger.error("OpenWeather error (%s): %s", err.code, err.message)
        return False

    ctx = build_context(cfg, weather)
    ctx["battery_soc"] = soc
    ctx["is_charging"] = is_charging

    html = TEMPLATE.render(**ctx)

    with tempfile.TemporaryDirectory() as td:
        png = Path(td) / "dash.png"
        html_to_png(html, png, preview=preview)

        if not preview:  # Pi / production path
            # mode 0 = full white‑black‑white, mode 2 = GC16 partial
            display_png(png, mode_override=0 if full_refresh else 2)

    return True


# ─────────────────────────── entrypoint ───────────────────────────────────────


def main() -> None:
    ap = argparse.ArgumentParser(description="E‑Ink Weather Display")
    ap.add_argument("--config", type=Path, required=True)
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    cfg = load_config(args.config)
    base_minutes = cfg.get("refresh_minutes", 120)

    pijuice = get_pijuice()
    ensure_rtc_synced(pijuice)

    error_streak = 0
    last_full_refresh = datetime.now()

    while True:
        full_refresh = datetime.now() - last_full_refresh > FULL_REFRESH_INTERVAL
        soc = get_soc(pijuice)
        is_charging = False
        if pijuice:
            try:
                stat = pijuice.status.GetStatus()["data"]
                is_charging = stat.get("powerInput") == "GOOD"
            except Exception:
                pass
        ok = cycle(
            cfg,
            preview=args.preview,
            full_refresh=full_refresh,
            soc=soc,
            is_charging=is_charging,
        )
        if ok:
            error_streak = 0
            if full_refresh:
                last_full_refresh = datetime.now()
        else:
            error_streak += 1
            if error_streak >= 3:
                logger.warning("3 consecutive failures → backing off ×4 interval")
                time.sleep(base_minutes * 4 * 60)
                continue

        if args.once:
            break

        sleep_min = base_minutes * 2 if soc < 25 else base_minutes
        logger.info("Battery %02d%% → sleeping %d min", soc, sleep_min)
        time.sleep(sleep_min * 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
