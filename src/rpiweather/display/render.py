"""Dashboard rendering helpers (Jinja environment, filters, html→png)."""

from __future__ import annotations

from typing import Any
import platform
import re
import subprocess
import zoneinfo
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from jinja2 import Environment, FileSystemLoader, Template, Undefined, select_autoescape

from rpiweather.weather.helpers import (
    deg_to_cardinal,
    get_moon_phase_icon_filename,
    get_moon_phase_label,
    get_weather_icon_filename,
    hourly_precip,
    beaufort_from_speed,
)
from rpiweather.weather.api import WeatherResponse
from rpiweather.config import WeatherConfig

PROJECT_ROOT = Path(__file__).resolve().parents[3]  # repo root

# ─────────────────────────── Jinja ENV ──────────────────────────


ENV = Environment(
    loader=FileSystemLoader(PROJECT_ROOT / "templates"),
    autoescape=select_autoescape(["html"]),
)


def wind_rotation(deg: float, direction: str = "towards") -> float:  # noqa: D401
    """Return adjusted wind bearing for 'from' or 'towards' arrow."""
    return deg if direction == "towards" else (deg + 180) % 360


ENV.filters.update(
    {
        "deg_to_cardinal": deg_to_cardinal,
        "weather_icon": get_weather_icon_filename,
        "moon_phase_icon": get_moon_phase_icon_filename,
        "wind_rotation": wind_rotation,
    }
)
ENV.filters["moon_phase_label"] = get_moon_phase_label

LOCAL_TZ = zoneinfo.ZoneInfo("America/New_York")
FULL_REFRESH_INTERVAL = timedelta(hours=24)


# ─────────────────────────── Jinja date‑time filters ──────────────────────


def ts_to_local(ts: int) -> datetime:
    """Convert POSIX timestamp to local datetime."""
    return datetime.fromtimestamp(ts, tz=LOCAL_TZ)


def dt_format(d: datetime, fmt: str = "%-I %p") -> str:
    """strftime wrapper usable as a Jinja filter."""
    if isinstance(fmt, Undefined):
        fmt = "%-I %p"
    return d.strftime(fmt)


ENV.filters["ts_to_dt"] = ts_to_local
ENV.filters["strftime"] = dt_format

# load template after all custom filters are registered
TEMPLATE: Template = ENV.get_template("dashboard.html.j2")

# ─────────────────────────── HTML → PNG ─────────────────────────


def html_to_png(html: str, out: Path, preview: bool = False) -> None:
    """
    Render HTML to PNG using wkhtmltoimage (xvfb-run on Linux headless).

    In preview mode on macOS/Windows, open in the default browser instead.
    """
    if preview and platform.system() != "Linux":
        out_dir = PROJECT_ROOT / "preview"
        out_dir.mkdir(parents=True, exist_ok=True)

        html_path = out_dir / "dash-preview.html"
        html_local = re.sub(r'(href|src)="/static/', r'\1="static/', html)
        html_path.write_text(html_local, "utf-8")

        import webbrowser  # local import

        webbrowser.open(html_path.as_uri())
        return

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


# ─────────────────────────── Dashboard Context Builder ──────────────────────────


def build_dashboard_context(
    cfg: WeatherConfig,
    weather: WeatherResponse,
    soc: int,
    is_charging: bool,
    battery_warning: bool,
) -> dict[str, Any]:
    """Build the dashboard template context."""

    now = datetime.now(ZoneInfo(cfg.timezone))
    today_local = now.date()

    max_uvi_time = None

    uvi_slice = [
        (h.dt, h.uvi)
        for h in weather.hourly
        if h.dt.astimezone().date() == today_local and h.uvi is not None
    ]
    if uvi_slice:
        max_uvi_entry = max(uvi_slice, key=lambda x: x[1])
        max_uvi_time = max_uvi_entry[0].astimezone()
        max_uvi_time_str = max_uvi_time.strftime(cfg.time_format_general)
    else:
        max_uvi_time_str = None

    sunrise_dt = weather.current.sunrise
    sunset_dt = weather.current.sunset

    sunrise_str = sunrise_dt.strftime(cfg.time_format_general)
    sunset_str = sunset_dt.strftime(cfg.time_format_general)

    moon_phase = weather.daily[0].moon_phase if weather.daily else 0.0

    hourly = [h for h in weather.hourly if h.dt.astimezone() > now][: cfg.hourly_count]
    for h in hourly:
        h.local_time = h.dt.astimezone().strftime(cfg.time_format_hourly)

    daily = [d for d in weather.daily if d.dt.astimezone().date() > today_local][
        : cfg.daily_count
    ]

    for d in daily:
        d.weekday_short = d.dt.astimezone().strftime("%a")

    ctx = {
        "now": now,
        "date": now.strftime("%A, %B %-d"),
        "last_refresh": now.strftime(cfg.time_format_general + " %Z"),
        "soc": soc,
        "battery_soc": soc,
        "battery_warning": battery_warning,
        "is_charging": is_charging,
        "units_temp": "°C" if cfg.units == "metric" else "°F",
        "units_wind": "m/s" if cfg.units == "metric" else "mph",
        "units_pressure": "hPa" if cfg.units == "metric" else "inHg",
        "hourly": hourly,
        "daily": daily,
        "sunrise": sunrise_str,
        "sunset": sunset_str,
        "moon_phase": moon_phase,
        "moon_phase_icon": get_moon_phase_icon_filename,
        "moon_phase_label": get_moon_phase_label,
        "uvi_time": max_uvi_time_str,
        "current": weather.current,
        "hourly_precip": hourly_precip,
        "city": cfg.city,
        "daylight": f"{(sunset_dt - sunrise_dt).seconds // 3600}h {(sunset_dt - sunrise_dt).seconds % 60}m",
        "uvi_max": max((uvi[1] for uvi in uvi_slice), default=0),
        "uvi_occurred": max_uvi_time is not None and now > max_uvi_time,
        "bft": beaufort_from_speed(weather.current.wind_speed),
        "aqi": weather.air_quality.aqi if weather.air_quality else "N/A",
    }

    return ctx
