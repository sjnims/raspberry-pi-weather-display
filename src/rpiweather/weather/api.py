from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Final, Any, Dict, Callable, cast
from functools import partial
import json

import requests
from .models import WeatherResponse

from .errors import WeatherAPIError
from .helpers import (
    deg_to_cardinal,
    get_weather_icon_filename,
    beaufort_from_speed,
    hourly_precip,
    get_moon_phase_icon_filename,
    get_moon_phase_label,
)

from rpiweather.config import WeatherConfig

API_URL: Final = "https://api.openweathermap.org/data/3.0/onecall"

# Human‑readable explanations for common HTTP errors
HTTP_ERROR_MAP: Final = {
    400: "Bad request - check lat/lon or parameters",
    401: "Invalid or missing API key",
    403: "Account blocked / key revoked",
    404: "Coordinates returned no data",
    429: "Rate limit exceeded",
    500: "OpenWeather internal error",
    502: "Bad gateway at OpenWeather",
    503: "Service unavailable (maintenance)",
    504: "Gateway timeout",
}


def fetch_weather(cfg: WeatherConfig) -> WeatherResponse:
    """Retrieve weather and air quality data."""
    # Get the main weather data
    params = {
        "lat": cfg.lat,
        "lon": cfg.lon,
        "appid": cfg.api_key,
        "units": getattr(cfg, "units", "imperial"),
        "exclude": "minutely,alerts",
    }

    try:
        resp = requests.get(API_URL, params=params, timeout=10)
    except requests.RequestException as exc:
        raise WeatherAPIError(0, f"Network error: {exc}") from exc

    if resp.status_code != 200:
        try:
            msg = resp.json().get(
                "message",
                HTTP_ERROR_MAP.get(resp.status_code, resp.text),
            )
        except ValueError:
            msg = HTTP_ERROR_MAP.get(resp.status_code, resp.text)
        raise WeatherAPIError(resp.status_code, msg)

    weather_json = resp.text  # store text for single parse

    # Merge AQI data into the raw dict before validation
    merged_raw: Dict[str, Any] = json.loads(weather_json)
    try:
        merged_raw["air_quality"] = fetch_air_quality(cfg)
    except Exception:
        merged_raw["air_quality"] = {"aqi": "N/A"}

    # Validate and convert to Pydantic model
    return WeatherResponse.model_validate(merged_raw)


def fetch_air_quality(cfg: WeatherConfig) -> dict[str, Any]:
    """Retrieve air quality data from OpenWeather API."""
    AQI_URL = "https://api.openweathermap.org/data/2.5/air_pollution"

    params = {
        "lat": cfg.lat,
        "lon": cfg.lon,
        "appid": cfg.api_key,
    }

    try:
        resp = requests.get(AQI_URL, params=params, timeout=10)
    except requests.RequestException as _exc:
        # Don't fail the whole request if AQI is unavailable
        return {"aqi": "N/A"}

    if resp.status_code != 200:
        return {"aqi": "N/A"}

    data = resp.json()

    # Extract the AQI value - OpenWeather uses a 1-5 scale:
    # 1: Good, 2: Fair, 3: Moderate, 4: Poor, 5: Very Poor
    try:
        aqi_value = data["list"][0]["main"]["aqi"]
        aqi_labels = ["", "Good", "Fair", "Moderate", "Poor", "Very Poor"]
        return {
            "aqi": aqi_labels[aqi_value],
            "aqi_value": aqi_value,
            "components": data["list"][0]["components"],
        }
    except (KeyError, IndexError):
        return {"aqi": "N/A"}


def build_context(cfg: WeatherConfig, weather: WeatherResponse) -> dict[str, Any]:
    """Transform raw API JSON into template-friendly context."""
    now = datetime.now(timezone.utc).astimezone()
    today = now.date()

    # Sun timings (already UTC in model)
    sunrise_dt = weather.current.sunrise.astimezone()
    sunset_dt = weather.current.sunset.astimezone()

    daylight_seconds = int(
        (weather.current.sunset - weather.current.sunrise).total_seconds()
    )
    daylight_hours, remainder = divmod(daylight_seconds, 3600)
    daylight_minutes = remainder // 60

    # ── UVI maxima ───────────────────────────────────────────────────────────
    uvi_data: list[tuple[int, float]] = [
        # include current observation first
        (int(weather.current.dt.timestamp()), weather.current.uvi or 0.0)
    ]

    for hour in weather.hourly:
        hour_local = hour.dt.astimezone()
        if hour_local.date() == today:
            uvi_data.append((int(hour.dt.timestamp()), hour.uvi or 0.0))

    if uvi_data:
        max_uvi_entry = max(uvi_data, key=lambda x: x[1])
        max_uvi_value = max_uvi_entry[1]
        max_uvi_time = datetime.fromtimestamp(
            max_uvi_entry[0], tz=timezone.utc
        ).astimezone()
    else:  # late in day, fallback
        max_uvi_value = weather.current.uvi or 0.0
        max_uvi_time = now

    # cache once to avoid repeated dict look‑ups
    is_future = max_uvi_time > now

    # ── Air‑quality & moon phase ─────────────────────────────────────────────
    aqi = (weather.model_extra or {}).get("air_quality", {}).get("aqi", "N/A")
    moon_phase = weather.daily[0].moon_phase if weather.daily else 0.0

    # ── Wind helpers ─────────────────────────────────────────────────────────
    speed = weather.current.wind_speed or 0.0
    if cfg.units != "imperial":
        speed *= 2.23694  # m/s → mph for Beaufort helper

    # Round wind direction to the nearest 10° for smoother icon rotation
    arrow_deg_raw: float = float(weather.current.wind_deg or 0)
    arrow_deg = int((round(arrow_deg_raw / 10) * 10) % 360)

    # --- Daily list: first N forecast days strictly *after* the *local* day ---
    loc_tz = timezone(timedelta(seconds=weather.timezone_offset))
    today_local = now.astimezone(loc_tz).date()

    # Skip any entry whose local date is today **or tomorrow** so that the
    # multi‑day strip begins the day after tomorrow (e.g. Thu if now is Tue).
    tomorrow_local = today_local + timedelta(days=1)

    future_daily = [
        d for d in weather.daily if d.dt.astimezone(loc_tz).date() > tomorrow_local
    ][: cfg.daily_count]

    # Precompute local_time strings for each hourly forecast object
    for h in weather.hourly:
        h.local_time = h.dt.astimezone().strftime(cfg.time_format)

    # Precompute weekday_short string for each daily forecast object
    for d in weather.daily:
        d.weekday_short = d.dt.astimezone().strftime("%a")

    return {
        # meta
        "date": now.strftime("%A, %B %d %Y"),
        "city": cfg.city,
        "last_refresh": now.strftime(cfg.time_format + " %Z"),
        "units_temp": "°F" if cfg.units == "imperial" else "°C",
        "units_wind": "mph" if cfg.units == "imperial" else "m/s",
        "units_precip": "in" if cfg.units == "imperial" else "mm",
        # current conditions
        "current": weather.current,
        # sun
        "sunrise": sunrise_dt.strftime(cfg.time_format),
        "sunset": sunset_dt.strftime(cfg.time_format),
        "daylight": f"{daylight_hours}h {daylight_minutes}m",
        # UV
        "uvi_max": f"{max_uvi_value:.1f}",
        "uvi_time": max_uvi_time.strftime(cfg.time_format),
        "uvi_occurred": not is_future,
        # AQI & moon
        "aqi": aqi,
        "moon_phase": moon_phase,
        # wind / Beaufort
        "bft": beaufort_from_speed(speed),
        # forecast slices
        # --- Hourly list: next N hours starting *after now* in local time -----
        "hourly": [h for h in weather.hourly if h.dt.astimezone() > now][
            : cfg.hourly_count
        ],
        "daily": future_daily,
        # helper filters
        "deg_to_cardinal": deg_to_cardinal,
        "arrow_deg": arrow_deg,
        "weather_icon": get_weather_icon_filename,
        # bind metric/imperial choice once so templates stay simple
        "hourly_precip": cast(
            Callable[[Any], str],
            partial(hourly_precip, imperial=(cfg.units == "imperial")),
        ),
        "moon_phase_icon": get_moon_phase_icon_filename,
        "moon_phase_label": get_moon_phase_label,
    }
