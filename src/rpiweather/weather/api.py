"""Weather API client for OpenWeather."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta, date
from typing import Final, Any, Dict, Callable, cast
from functools import partial
import json
import logging

import requests
from .models import WeatherResponse
from .errors import WeatherAPIError, NetworkError
from .utils import (
    UnitConverter,
    WeatherIcons,
    PrecipitationUtils,
)

from rpiweather.settings import UserSettings
from rpiweather.weather.models import Daily
from rpiweather.utils import TimeUtils

logger = logging.getLogger(__name__)

# API endpoints
API_URL: Final = "https://api.openweathermap.org/data/3.0/onecall"
AQI_URL: Final = "https://api.openweathermap.org/data/2.5/air_pollution"

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


class WeatherAPI:
    """OpenWeather API client for the One Call API.

    Handles API requests, network error handling, rate limiting, and
    caching for the OpenWeather One Call API. Transforms raw JSON responses
    into strongly-typed WeatherResponse objects.

    Requires a valid API key and location coordinates from user settings.
    """

    def __init__(self, config: UserSettings, timeout: int = 10) -> None:
        """Initialize the weather API client.

        Args:
            config: Weather configuration with API key and location
            timeout: Timeout for API requests in seconds
        """
        self.config = config
        self.timeout = timeout

    def fetch_weather(self) -> WeatherResponse:
        """Retrieve weather and air quality data.

        Makes API requests to OpenWeather One Call API and Air Quality API,
        merges the responses, and validates them into a strongly-typed model.

        Returns:
            Validated WeatherResponse object including weather and air quality data

        Raises:
            NetworkError: When network connectivity issues occur
            AuthenticationError: When API key is invalid
            RateLimitError: When API rate limits are exceeded
            WeatherAPIError: For other API-related errors
        """
        # Get the main weather data
        params = {
            "lat": self.config.lat,
            "lon": self.config.lon,
            "appid": self.config.api_key,
            "units": getattr(self.config, "units", "imperial"),
            "exclude": "minutely,alerts",
        }

        try:
            resp = requests.get(API_URL, params=params, timeout=self.timeout)
        except requests.RequestException as exc:
            logger.warning("Weather API network error: %s", exc)
            raise NetworkError(f"Network error: {exc}", exc) from exc

        if resp.status_code != 200:
            try:
                msg = resp.json().get(
                    "message",
                    HTTP_ERROR_MAP.get(resp.status_code, resp.text),
                )
            except ValueError:
                msg = HTTP_ERROR_MAP.get(resp.status_code, resp.text)
            logger.error("Weather API error: %s - %s", resp.status_code, msg)
            raise WeatherAPIError(resp.status_code, msg)

        weather_json = resp.text  # store text for single parse

        # Merge AQI data into the raw dict before validation
        merged_raw: Dict[str, Any] = json.loads(weather_json)
        try:
            aqi_raw = self.fetch_air_quality()
            merged_raw["air_quality"] = {
                "aqi": aqi_raw.get("aqi", "N/A"),
                "aqi_value": aqi_raw.get("aqi_value", 0),
                "components": aqi_raw.get("components", None),
            }
        except Exception as exc:
            logger.info("Could not fetch air quality: %s", exc)
            merged_raw["air_quality"] = {"aqi": "N/A", "aqi_value": 0}

        # Validate and convert to Pydantic model
        return WeatherResponse.model_validate(merged_raw)

    def fetch_air_quality(self) -> dict[str, Any]:
        """Retrieve air quality data from OpenWeather API.

        Returns:
            Dictionary with air quality data
        """
        params = {
            "lat": self.config.lat,
            "lon": self.config.lon,
            "appid": self.config.api_key,
        }

        try:
            resp = requests.get(AQI_URL, params=params, timeout=self.timeout)
        except requests.RequestException as exc:
            # Don't fail the whole request if AQI is unavailable
            logger.info("Air quality API network error: %s", exc)
            return {"aqi": "N/A"}

        if resp.status_code != 200:
            logger.info("Air quality API error: %s", resp.status_code)
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
        except (KeyError, IndexError) as exc:
            logger.warning("Could not parse air quality data: %s", exc)
            return {"aqi": "N/A"}

    def build_context(self, weather: WeatherResponse) -> dict[str, Any]:
        """Build template context dictionary from weather data.

        Processes raw weather data into a form ready for template rendering:
        - Formats dates and times according to user preferences
        - Calculates derived values (UV index time, daylight hours)
        - Prepares helper functions for templates
        - Sets up measurement unit labels based on user preferences

        Args:
            weather: Weather data response object

        Returns:
            Dictionary with processed values ready for template rendering
        """
        now = datetime.now(timezone.utc).astimezone()
        today = now.date()
        cfg = self.config

        # Sun timings (already UTC in model)
        sunrise_dt = weather.current.sunrise.astimezone()
        sunset_dt = weather.current.sunset.astimezone()

        daylight_seconds = int(
            (weather.current.sunset - weather.current.sunrise).total_seconds()
        )
        daylight_hours, remainder = divmod(daylight_seconds, 3600)
        daylight_minutes = remainder // 60

        # UVI maxima
        uvi_data = self._calculate_uvi_data(weather, today)
        max_uvi_value, max_uvi_time = self._get_max_uvi(uvi_data, weather, now)
        is_future = max_uvi_time > now

        # Air quality & moon phase
        aqi = (weather.model_extra or {}).get("air_quality", {}).get("aqi", "N/A")
        moon_phase = weather.daily[0].moon_phase if weather.daily else 0.0

        # Wind helpers
        speed, arrow_deg = self._process_wind_data(weather, cfg)

        # Daily forecasts
        future_daily = self._get_future_daily(weather, now, cfg)

        # Precompute display strings
        self._precompute_display_strings(weather, cfg)

        return {
            # meta
            "date": now.strftime("%A, %B %d %Y"),
            "city": cfg.city,
            "last_refresh": now.strftime(cfg.time_format_general + " %Z"),
            "units_temp": "°F" if cfg.units == "imperial" else "°C",
            "units_wind": "mph" if cfg.units == "imperial" else "m/s",
            "units_precip": "in" if cfg.units == "imperial" else "mm",
            # current conditions
            "current": weather.current,
            # sun
            "sunrise": sunrise_dt.strftime(cfg.time_format_general),
            "sunset": sunset_dt.strftime(cfg.time_format_general),
            "daylight": f"{daylight_hours}h {daylight_minutes}m",
            # UV
            "uvi_max": f"{max_uvi_value:.1f}",
            "uvi_time": max_uvi_time.strftime(cfg.time_format_general),
            "uvi_occurred": not is_future,
            # AQI & moon
            "aqi": aqi,
            "moon_phase": moon_phase,
            # wind / Beaufort
            "bft": UnitConverter.beaufort_from_speed(speed),
            # forecast slices
            "hourly": [h for h in weather.hourly if h.dt.astimezone() > now][
                : cfg.hourly_count
            ],
            "daily": future_daily,
            # helper filters
            "deg_to_cardinal": UnitConverter.deg_to_cardinal,
            "arrow_deg": arrow_deg,
            "weather_icon": WeatherIcons.get_icon_filename,
            # bind metric/imperial choice once so templates stay simple
            "hourly_precip": cast(
                Callable[[Any], str],
                partial(
                    PrecipitationUtils.hourly_precip, imperial=(cfg.units == "imperial")
                ),
            ),
            "moon_phase_icon": WeatherIcons.get_moon_phase_icon,
            "moon_phase_label": WeatherIcons.get_moon_phase_label,
        }

    # Private helper methods
    def _calculate_uvi_data(
        self, weather: WeatherResponse, today: date
    ) -> list[tuple[int, float]]:
        """Calculate UV index data points for the day."""
        uvi_data: list[tuple[int, float]] = [
            # include current observation first
            (int(weather.current.dt.timestamp()), weather.current.uvi or 0.0)
        ]

        for hour in weather.hourly:
            hour_local = hour.dt.astimezone()
            if hour_local.date() == today:
                uvi_data.append((int(hour.dt.timestamp()), hour.uvi or 0.0))

        return uvi_data

    def _get_max_uvi(
        self, uvi_data: list[tuple[int, float]], weather: WeatherResponse, now: datetime
    ) -> tuple[float, datetime]:
        """Get the maximum UV index value and time."""
        if uvi_data:
            max_uvi_entry = max(uvi_data, key=lambda x: x[1])
            max_uvi_value = max_uvi_entry[1]
            max_uvi_time = TimeUtils.to_local_datetime(max_uvi_entry[0], "UTC")
        else:  # late in day, fallback
            max_uvi_value = weather.current.uvi or 0.0
            max_uvi_time = now

        return max_uvi_value, max_uvi_time

    def _process_wind_data(
        self, weather: WeatherResponse, cfg: UserSettings
    ) -> tuple[float, int]:
        """Process wind speed and direction data."""
        speed = weather.current.wind_speed or 0.0
        if cfg.units != "imperial":
            speed *= 2.23694  # m/s → mph for Beaufort helper

        # Round wind direction to the nearest 10° for smoother icon rotation
        arrow_deg_raw: float = float(weather.current.wind_deg or 0)
        arrow_deg = int((round(arrow_deg_raw / 10) * 10) % 360)

        return speed, arrow_deg

    def _get_future_daily(
        self, weather: WeatherResponse, now: datetime, cfg: UserSettings
    ) -> list[Daily]:  # Add this return type
        """Get daily forecasts starting from tomorrow.

        Args:
            weather: Weather response object
            now: Current datetime
            cfg: Weather configuration

        Returns:
            List of daily forecast objects for future days
        """
        loc_tz = now.tzinfo or timezone.utc
        today_local = now.date()
        tomorrow_local = today_local + timedelta(days=1)

        return [
            d for d in weather.daily if d.dt.astimezone(loc_tz).date() >= tomorrow_local
        ][: cfg.daily_count]

    def _precompute_display_strings(
        self, weather: WeatherResponse, cfg: UserSettings
    ) -> None:
        """Precompute display strings for hourly and daily forecasts."""
        # Precompute local_time strings for each hourly forecast object
        for h in weather.hourly:
            h.local_time = h.dt.astimezone().strftime(cfg.time_format_hourly)

        # Precompute weekday_short string for each daily forecast object
        for d in weather.daily:
            d.weekday_short = d.dt.astimezone().strftime("%a")
