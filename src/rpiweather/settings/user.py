"""User-configurable settings loaded from config.yaml."""

from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path
from typing import ClassVar, Literal
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

# Load environment variables from .env file(s)
load_dotenv()


def _interpolate_env(content: str) -> str:
    return re.sub(r"\$\{(\w+)\}", lambda m: os.getenv(m.group(1), ""), content)


class QuietHours(BaseModel):
    """Time window (24-hour) during which refreshes are skipped.

    Hours are integers from 0 to 23 inclusive.
    """

    start: int = Field(..., ge=0, le=23, description="Hour of day to begin sleeping (0-23)")
    end: int = Field(..., ge=0, le=23, description="Hour of day to end sleeping (0-23)")

    @model_validator(mode="after")
    def check_start_not_equal_end(self) -> QuietHours:
        if self.start == self.end:
            raise ValueError("quiet_hours start and end cannot be the same")
        return self

    def is_quiet_time(self, current_time: datetime | None = None) -> bool:
        """Check if the current or specified time is within quiet hours.

        Args:
            current_time: Time to check (default: current time)

        Returns:
            True if within quiet hours
        """
        now = current_time or datetime.now()
        current_hour = now.hour

        if self.start < self.end:
            # Simple case: quiet hours within same day
            return self.start <= current_hour < self.end

        # Complex case: quiet hours span midnight
        return current_hour >= self.start or current_hour < self.end


class UserSettings(BaseModel):
    """User settings for the application behavior, and for the physical
    e-ink display. These values can be overridden by user settings in
    config.yaml.

    Default values are set for the 10.3" 1872x1404 Waveshare e-ink HAT display.
    """

    # Default search paths for configuration
    DEFAULT_CONFIG_PATHS: ClassVar[list[Path]] = [
        Path("config.yaml"),
        Path("~/.config/rpiweather/config.yaml").expanduser(),
        Path("/etc/rpiweather/config.yaml"),
    ]

    # Location settings
    lat: float = Field(..., description="Latitude")
    lon: float = Field(..., description="Longitude")
    api_key: str = Field(..., min_length=10, description="OpenWeather API key")
    units: Literal["imperial", "metric"] = "imperial"
    city: str = Field(..., description="Display name of location")

    # Display settings
    refresh_minutes: int = Field(120, gt=0, description="Base refresh interval (minutes)")
    hourly_count: int = Field(8, ge=1, le=24, description="Hours to show in forecast slice")
    daily_count: int = Field(5, ge=1, le=7, description="Days to show in forecast slice")
    display_width: int = Field(1872, gt=0, description="Width of the display in pixels")
    display_height: int = Field(1404, gt=0, description="Height of the display in pixels")
    vcom_volts: float = Field(
        -1.45,
        ge=-2.0,
        le=0.0,
        description='VCOM voltage for the display (-1.45 for 10.3" HAT)',
    )

    # Power management
    poweroff_soc: int = Field(
        8,
        ge=0,
        le=100,
        description="Battery % threshold below which the Pi shuts down instead of sleeping",
    )

    # Time formatting
    time_format_general: str = Field(
        "%-I:%M %p", description="General time display format (e.g. 6:04 AM)"
    )
    time_format_hourly: str = Field(
        "%-I %p", description="Hourly forecast time display format (e.g. 6 AM)"
    )
    time_format_daily: str = Field("%a", description="Daily forecast format (e.g. Mon)")
    time_format_full_date: str = Field(
        "%A, %B %-d", description="Full date format (e.g. Monday, January 3)"
    )
    timezone: str = Field("America/New_York", description="Local timezone for display formatting")

    # Schedule settings
    quiet_hours: QuietHours | None = None
    stay_awake_url: str | None = Field(
        None,
        description="Override URL that returns {'awake': true|false}; "
        "if null, CLI option or default is used",
    )

    # ---- validators ----
    @field_validator("quiet_hours")
    @classmethod
    def validate_quiet(cls, v: QuietHours | None) -> QuietHours | None:
        return v

    # ---- convenience methods ----
    def get_timezone(self) -> ZoneInfo:
        """Get configured timezone as ZoneInfo object.

        Returns:
            ZoneInfo object for the configured timezone
        """
        return ZoneInfo(self.timezone)

    def is_quiet_time(self, current_time: datetime | None = None) -> bool:
        """Check if the current or specified time is within quiet hours.

        Args:
            current_time: Time to check (default: current time)

        Returns:
            True if quiet hours are enabled and the time is within them
        """
        if not self.quiet_hours:
            return False
        return self.quiet_hours.is_quiet_time(current_time)

    def is_critical_battery(self, soc: int) -> bool:
        """Check if the battery state of charge is critically low.

        Args:
            soc: Battery state of charge percentage

        Returns:
            True if the battery is below the poweroff threshold
        """
        return soc <= self.poweroff_soc

    def format_time(self, dt: datetime, hourly: bool = False) -> str:
        """Format a datetime according to configured time format.

        Args:
            dt: Datetime to format
            hourly: If True, use hourly format instead of general format

        Returns:
            Formatted time string
        """
        # Ensure datetime has timezone
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=self.get_timezone())

        fmt = self.time_format_hourly if hourly else self.time_format_general
        return dt.strftime(fmt)

    @property
    def is_metric(self) -> bool:
        """Whether the user has selected metric units."""
        return self.units == "metric"

    @property
    def is_imperial(self) -> bool:
        """Whether the user has selected imperial units."""
        return self.units == "imperial"

    @classmethod
    def load(cls, path: Path | None = None) -> UserSettings:
        """Load configuration from a YAML file.

        Args:
            path: Path to config file (optional, searches default locations if None)

        Returns:
            Validated UserSettings object

        Raises:
            FileNotFoundError: If no config file is found
            RuntimeError: If the config file cannot be parsed or is invalid
        """
        # Try to find config file
        if path is None:
            # Check environment variable first
            env_path = os.environ.get("RPIWEATHER_CONFIG")
            if env_path:
                path = Path(env_path)
                if not path.exists():
                    raise FileNotFoundError(f"Config file from RPIWEATHER_CONFIG not found: {path}")
            else:
                # Try default paths
                for default_path in cls.DEFAULT_CONFIG_PATHS:
                    if default_path.exists():
                        path = default_path
                        break
                else:
                    raise FileNotFoundError(
                        "No configuration file found. Create config.yaml or set RPIWEATHER_CONFIG."
                    )

        # Load and parse config
        import yaml  # local import to avoid hard dep for callers

        try:
            raw = _interpolate_env(path.read_text())
            data = yaml.safe_load(raw)
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(f"Unable to read config YAML: {exc}") from exc

        try:
            return cls.model_validate(data)
        except ValidationError as err:
            raise RuntimeError(f"Invalid configuration:\n{err}") from err
