"""Typed models for OpenWeather OneCall 3.0 responses.

Only the fields used by the dashboard are modelled for now; add more as needed.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field

from rpiweather.models.base import TimeStampModel
from rpiweather.weather.air_quality import AirQuality

# ─────────────────────────── primitives ──────────────────────────────────────


class Coord(BaseModel):
    """Geographic coordinates (latitude, longitude)."""

    lat: float
    lon: float


class WeatherCondition(BaseModel):
    """Weather condition information from OpenWeather."""

    id: int
    main: str
    description: str
    icon: str

    @property
    def is_day(self) -> bool:
        """Check if this icon represents daytime conditions.

        Returns:
            True for daytime, False for nighttime
        """
        return not self.icon.endswith("n")

    @property
    def is_clear(self) -> bool:
        """Check if this condition represents clear weather.

        Returns:
            True for clear sky conditions
        """
        return self.id == 800

    @property
    def is_rain(self) -> bool:
        """Check if this condition represents rain.

        Returns:
            True for rain conditions
        """
        return 500 <= self.id < 600


# ─────────────────────────── composite blocks ────────────────────────────────


class Current(TimeStampModel):
    """Current weather conditions."""

    dt: datetime
    sunrise: datetime
    sunset: datetime
    temp: float
    feels_like: float = Field(..., alias="feels_like")
    pressure: int
    humidity: int
    wind_speed: float
    wind_deg: int
    uvi: float | None = None
    visibility: int | None = None
    weather: list[WeatherCondition]
    sunrise_local: str | None = None
    sunset_local: str | None = None

    model_config = ConfigDict(extra="allow")

    # Use TimeStampModel validator factory method instead of duplicating
    _validate_dt = TimeStampModel.timestamp_validator("dt")
    _validate_sunrise = TimeStampModel.timestamp_validator("sunrise")
    _validate_sunset = TimeStampModel.timestamp_validator("sunset")

    @property
    def is_day(self) -> bool:
        """Check if the current time is during daylight hours.

        Returns:
            True if the current time is between sunrise and sunset
        """
        now = self.dt
        return self.sunrise <= now < self.sunset

    @property
    def weather_main(self) -> WeatherCondition | None:
        """Get the primary weather condition.

        Returns:
            First weather condition in the list or None if not available
        """
        return self.weather[0] if self.weather else None

    @property
    def daylight_hours(self) -> float:
        """Calculate the number of daylight hours.

        Returns:
            Hours of daylight as a float
        """
        delta = self.sunset - self.sunrise
        return delta.total_seconds() / 3600


class Hourly(TimeStampModel):
    """Hourly forecast data."""

    dt: datetime
    temp: float
    wind_speed: float | None = None
    wind_deg: int | None = None
    uvi: float | None = None
    weather: list[WeatherCondition]
    local_time: str | None = None

    # Use TimeStampModel validator factory method
    _validate_dt = TimeStampModel.timestamp_validator("dt")

    @property
    def weather_main(self) -> WeatherCondition | None:
        """Get the primary weather condition.

        Returns:
            First weather condition in the list or None if not available
        """
        return self.weather[0] if self.weather else None

    @property
    def has_rain(self) -> bool:
        """Check if this hour has rain forecast."""
        if not self.weather:
            return False
        return any(500 <= w.id < 600 for w in self.weather)

    @property
    def has_snow(self) -> bool:
        """Check if this hour has snow forecast."""
        if not self.weather:
            return False
        return any(600 <= w.id < 700 for w in self.weather)


class DailyTemp(BaseModel):
    """Temperature variations throughout the day."""

    day: float
    night: float
    eve: float
    morn: float
    min: float
    max: float

    @property
    def range(self) -> float:
        """Calculate the daily temperature range.

        Returns:
            Difference between max and min temperatures
        """
        return self.max - self.min


class Daily(TimeStampModel):
    """Daily forecast data."""

    dt: datetime
    sunrise: datetime
    sunset: datetime
    temp: DailyTemp
    uvi: float | None = None
    moon_phase: float | None = None
    weather: list[WeatherCondition]
    sunrise_local: str | None = None
    sunset_local: str | None = None
    weekday_short: str | None = None

    model_config = ConfigDict(extra="allow")

    # Use TimeStampModel validator factory method
    _validate_dt = TimeStampModel.timestamp_validator("dt")
    _validate_sunrise = TimeStampModel.timestamp_validator("sunrise")
    _validate_sunset = TimeStampModel.timestamp_validator("sunset")

    @property
    def daylight_hours(self) -> float:
        """Calculate the number of daylight hours.

        Returns:
            Hours of daylight as a float
        """
        delta = self.sunset - self.sunrise
        return delta.total_seconds() / 3600

    @property
    def weather_main(self) -> WeatherCondition | None:
        """Get the primary weather condition.

        Returns:
            First weather condition in the list or None if not available
        """
        return self.weather[0] if self.weather else None

    # Moon phase constants for readability
    MOON_NEW: ClassVar[float] = 0.0
    MOON_FIRST_QUARTER: ClassVar[float] = 0.25
    MOON_FULL: ClassVar[float] = 0.5
    MOON_LAST_QUARTER: ClassVar[float] = 0.75

    @property
    def moon_phase_name(self) -> str:
        """Get the name of the current moon phase.

        Returns:
            String describing the moon phase
        """
        if self.moon_phase is None:
            return "Unknown"

        phase = self.moon_phase
        if phase == self.MOON_NEW:
            return "New Moon"
        elif phase < self.MOON_FIRST_QUARTER:
            return "Waxing Crescent"
        elif phase == self.MOON_FIRST_QUARTER:
            return "First Quarter"
        elif phase < self.MOON_FULL:
            return "Waxing Gibbous"
        elif phase == self.MOON_FULL:
            return "Full Moon"
        elif phase < self.MOON_LAST_QUARTER:
            return "Waning Gibbous"
        elif phase == self.MOON_LAST_QUARTER:
            return "Last Quarter"
        else:
            return "Waning Crescent"


# ─────────────────────────── top-level response ──────────────────────────────


class WeatherResponse(BaseModel):
    """Weather data container parsed from OpenWeather API response.

    Organizes weather data into logical components (current, hourly, daily)
    and validates the structure of API responses. Handles timezone conversions
    and ensures consistent data types across the application.
    """

    lat: float
    lon: float
    timezone: str
    timezone_offset: int
    current: Current
    hourly: list[Hourly]
    daily: list[Daily]
    air_quality: AirQuality | None = None

    @property
    def location(self) -> Coord:
        """Get the location coordinates.

        Returns:
            Coord object with lat/lon
        """
        return Coord(lat=self.lat, lon=self.lon)

    def get_timezone_info(self) -> timezone:
        """Get timezone object for the location.

        Returns:
            timezone object with the correct offset
        """
        return timezone(timedelta(seconds=self.timezone_offset))

    def get_daily_min_max(self) -> tuple[float, float]:
        """Get the minimum and maximum temperatures across the daily forecast.

        Returns:
            Tuple of (min_temp, max_temp)
        """
        if not self.daily:
            return (self.current.temp, self.current.temp)

        min_temp = min(day.temp.min for day in self.daily)
        max_temp = max(day.temp.max for day in self.daily)
        return (min_temp, max_temp)

    def filter_hourly(self, hours: int = 24) -> list[Hourly]:
        """Get a filtered list of hourly forecasts.

        Args:
            hours: Number of hours to include

        Returns:
            Filtered list of hourly forecasts
        """
        return self.hourly[:hours]

    @property
    def current_weather(self) -> WeatherCondition | None:
        """Get the primary current weather condition."""
        return self.current.weather_main if self.current else None
