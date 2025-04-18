from __future__ import annotations

from datetime import datetime, timezone
from typing import Final, Any, Dict

import requests

from .errors import WeatherAPIError
from .helpers import deg_to_cardinal, owm_icon_class, beaufort_from_speed, hourly_precip

API_URL: Final = "https://api.openweathermap.org/data/3.0/onecall"

# Human‑readable explanations for common HTTP errors
HTTP_ERROR_MAP: Final = {
    400: "Bad request – check lat/lon or parameters",
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
    """Retrieve the full One Call 3.0 payload and raise on any error."""
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

    return resp.json()


def build_context(cfg: Dict[str, Any], weather: Dict[str, Any]) -> Dict[str, Any]:
    """Transform raw API JSON into template‑friendly context."""
    now = datetime.now(timezone.utc).astimezone()

    return {
        # Meta
        "date": now.strftime("%A, %B %d %Y"),
        "city": cfg["city"],
        "last_refresh": now.strftime(
            "%I:%M %p %Z" if not cfg.get("time_24h") else "%H:%M %Z"
        ),
        "units_temp": "°F" if cfg["units"] == "imperial" else "°C",
        "units_wind": "mph" if cfg["units"] == "imperial" else "m/s",
        "units_precip": "in" if cfg["units"] == "imperial" else "mm",
        # Current conditions
        "current": weather["current"],
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
        # Helper filters (used directly in Jinja templates if desired)
        "deg_to_cardinal": deg_to_cardinal,
        "arrow_deg": int(round(weather["current"]["wind_deg"] / 5) * 5) % 360,
        "owm_icon": owm_icon_class,
        "hourly_precip": hourly_precip,
    }
