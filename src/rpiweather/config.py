from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import ClassVar, Literal, Optional

from pydantic import BaseModel, Field, ValidationError, field_validator
from zoneinfo import ZoneInfo


class QuietHours(BaseModel):
    """Time window (24-hour) during which refreshes are skipped.

    Hours are integers from 0 to 23 inclusive.
    """

    start: int = Field(
        ..., ge=0, le=23, description="Hour of day to begin sleeping (0-23)"
    )
    end: int = Field(..., ge=0, le=23, description="Hour of day to end sleeping (0-23)")

    def is_quiet_time(self, current_time: Optional[datetime] = None) -> bool:
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


class WeatherConfig(BaseModel):
    """Schema for config.yaml."""

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
    refresh_minutes: int = Field(
        120, gt=0, description="Base refresh interval (minutes)"
    )
    hourly_count: int = Field(
        8, ge=1, le=24, description="Hours to show in forecast slice"
    )
    daily_count: int = Field(
        5, ge=1, le=7, description="Days to show in forecast slice"
    )

    # Power management
    poweroff_soc: int = Field(
        8,
        ge=0,
        le=100,
        description="Battery % threshold below which the Pi shuts down "
        "instead of sleeping",
    )

    # Time formatting
    time_format_general: str = Field(
        "%-I:%M %p", description="General time display format (e.g. 6:04 AM)"
    )
    time_format_hourly: str = Field(
        "%-I %p", description="Hourly forecast time display format (e.g. 6 AM)"
    )
    timezone: str = Field(
        "America/New_York", description="Local timezone for display formatting"
    )

    # Schedule settings
    quiet_hours: Optional[QuietHours] = None
    stay_awake_url: Optional[str] = Field(
        None,
        description="Override URL that returns {'awake': true|false}; "
        "if null, CLI option or default is used",
    )

    # ---- validators ----
    @field_validator("quiet_hours")
    @classmethod
    def validate_quiet(
        cls, v: Optional[QuietHours]
    ) -> Optional[QuietHours]:  # noqa: D401
        """Ensure quiet_hours.start != quiet_hours.end."""
        if v and v.start == v.end:
            raise ValueError("quiet_hours start and end cannot be identical")
        return v

    # ---- convenience methods ----
    def get_timezone(self) -> ZoneInfo:
        """Get configured timezone as ZoneInfo object.

        Returns:
            ZoneInfo object for the configured timezone
        """
        return ZoneInfo(self.timezone)

    def is_quiet_time(self, current_time: Optional[datetime] = None) -> bool:
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

    @classmethod
    def load(cls, path: Optional[Path] = None) -> WeatherConfig:
        """Load configuration from a YAML file.

        Args:
            path: Path to config file (optional, searches default locations if None)

        Returns:
            Validated WeatherConfig object

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
                    raise FileNotFoundError(
                        f"Config file from RPIWEATHER_CONFIG not found: {path}"
                    )
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
            data = yaml.safe_load(path.read_text())
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(f"Unable to read config YAML: {exc}") from exc

        try:
            return cls.model_validate(data)
        except ValidationError as err:
            raise RuntimeError(f"Invalid configuration:\n{err}") from err
