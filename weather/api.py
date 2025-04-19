from __future__ import annotations

from datetime import datetime, timezone
from typing import Final, Any, Dict

import requests

from .errors import WeatherAPIError
from .helpers import deg_to_cardinal, owm_icon_class, beaufort_from_speed, hourly_precip

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


def fetch_weather(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Retrieve weather and air quality data."""
    # Get the main weather data (existing code)
    params = {
        "lat": cfg["lat"],
        "lon": cfg["lon"],
        "appid": cfg["api_key"],
        "units": cfg.get("units", "imperial"),
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

    weather_data = resp.json()

    # Add air quality data to the weather data
    try:
        air_quality = fetch_air_quality(cfg)
        weather_data["air_quality"] = air_quality
    except Exception:
        # Don't let air quality failures break the whole display
        weather_data["air_quality"] = {"aqi": "N/A"}

    return weather_data


def fetch_air_quality(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Retrieve air quality data from OpenWeather API."""
    AQI_URL = "https://api.openweathermap.org/data/2.5/air_pollution"

    params = {
        "lat": cfg["lat"],
        "lon": cfg["lon"],
        "appid": cfg["api_key"],
    }

    try:
        resp = requests.get(AQI_URL, params=params, timeout=10)
    except requests.RequestException as exc:
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


def build_context(cfg: Dict[str, Any], weather: Dict[str, Any]) -> Dict[str, Any]:
    """Transform raw API JSON into template-friendly context."""
    now = datetime.now(timezone.utc).astimezone()
    today = now.date()  # Get just the date part for comparison

    # Handle sunrise/sunset
    sunrise_dt = datetime.fromtimestamp(weather["current"]["sunrise"])
    sunset_dt = datetime.fromtimestamp(weather["current"]["sunset"])

    # Calculate daylight hours and minutes
    daylight_seconds = weather["current"]["sunset"] - weather["current"]["sunrise"]
    daylight_hours = int(daylight_seconds // 3600)
    daylight_minutes = int((daylight_seconds % 3600) // 60)

    # Find UVI max and time for current day only
    uvi_data: list[tuple[int, float]] = []

    # First check current hour
    current_uvi = weather["current"].get("uvi", 0)
    current_time = weather["current"]["dt"]
    uvi_data.append((current_time, current_uvi))

    # Then add all remaining hourly forecasts for today
    for hour in weather["hourly"]:
        hour_dt = datetime.fromtimestamp(hour["dt"])
        if hour_dt.date() == today:  # Only include hours from today
            uvi_data.append((hour["dt"], hour.get("uvi", 0)))

    # Find the maximum UVI value and its time
    max_uvi_entry = max(uvi_data, key=lambda x: x[1])
    max_uvi_value = max_uvi_entry[1]
    max_uvi_time = datetime.fromtimestamp(max_uvi_entry[0])

    # Format with indication of past/future
    is_future = max_uvi_time > now
    time_format = "%-I %p" if not cfg.get("time_24h") else "%-H:%M"

    # Handle edge case if no data for today (late in day)
    if not uvi_data:
        # Just use the current UVI value
        max_uvi_value = weather["current"].get("uvi", 0)
        max_uvi_time = now
    else:
        max_uvi_entry = max(uvi_data, key=lambda x: x[1])
        max_uvi_value = max_uvi_entry[1]
        max_uvi_time = datetime.fromtimestamp(max_uvi_entry[0])

    # Get AQI if available
    aqi = weather.get("air_quality", {}).get("aqi", "N/A")

    return {
        # Meta
        "date": now.strftime("%A, %B %d %Y"),
        "city": cfg["city"],
        "last_refresh": now.strftime(
            "%-I:%M %p %Z" if not cfg.get("time_24h") else "%-H:%M %Z"
        ),
        "units_temp": "°F" if cfg["units"] == "imperial" else "°C",
        "units_wind": "mph" if cfg["units"] == "imperial" else "m/s",
        "units_precip": "in" if cfg["units"] == "imperial" else "mm",
        # Current conditions
        "current": weather["current"],
        # Sun information
        "sunrise": sunrise_dt.strftime(
            "%-I:%M %p" if not cfg.get("time_24h") else "%-H:%M"
        ),
        "sunset": sunset_dt.strftime(
            "%-I:%M %p" if not cfg.get("time_24h") else "%-H:%M"
        ),
        "daylight": f"{daylight_hours}h {daylight_minutes}m",
        # UV information
        "uvi_max": f"{max_uvi_value:.1f}",
        "uvi_time": max_uvi_time.strftime(time_format),
        "uvi_occurred": not is_future,  # To indicate if it already happened
        # Air quality
        "aqi": aqi,
        # Moon phase
        "moon_phase": weather["daily"][0]["moon_phase"],
        # Beafort scale
        "bft": beaufort_from_speed(
            weather["current"]["wind_speed"]
            * (1 if cfg["units"] == "imperial" else 2.23694)
        ),
        # Forecast slices
        "hourly": weather["hourly"][: cfg.get("hourly_count", 8)],
        "daily": weather["daily"][1 : 1 + cfg.get("daily_count", 5)],
        # Helper filters (used directly in Jinja templates)
        "deg_to_cardinal": deg_to_cardinal,
        "arrow_deg": int(round(weather["current"]["wind_deg"] / 5) * 5) % 360,
        "owm_icon": owm_icon_class,
        "hourly_precip": hourly_precip,
    }
