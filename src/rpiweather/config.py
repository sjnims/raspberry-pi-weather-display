from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationError, field_validator


class QuietHours(BaseModel):
    """Time window (24-hour) during which refreshes are skipped.

    Hours are integers from 0 to 23 inclusive.
    """

    start: int = Field(
        ..., ge=0, le=23, description="Hour of day to begin sleeping (0-23)"
    )
    end: int = Field(..., ge=0, le=23, description="Hour of day to end sleeping (0-23)")


class WeatherConfig(BaseModel):
    """Schema for config.yaml."""

    lat: float = Field(..., description="Latitude")
    lon: float = Field(..., description="Longitude")
    api_key: str = Field(..., min_length=10, description="OpenWeather API key")
    units: Literal["imperial", "metric"] = "imperial"
    city: str = Field(..., description="Display name of location")
    refresh_minutes: int = Field(
        120, gt=0, description="Base refresh interval (minutes)"
    )
    hourly_count: int = Field(
        8, ge=1, le=24, description="Hours to show in forecast slice"
    )
    daily_count: int = Field(
        5, ge=1, le=7, description="Days to show in forecast slice"
    )
    poweroff_soc: int = Field(
        8,
        ge=0,
        le=100,
        description="Battery % threshold below which the Pi shuts down "
        "instead of sleeping",
    )
    time_format_general: str = Field(
        "%-I:%M %p", description="General time display format (e.g. 6:04 AM)"
    )
    time_format_hourly: str = Field(
        "%-I %p", description="Hourly forecast time display format (e.g. 6 AM)"
    )
    timezone: str = Field(
        "America/New_York", description="Local timezone for display formatting"
    )
    quiet_hours: QuietHours | None = None

    stay_awake_url: str | None = Field(
        None,
        description="Override URL that returns {'awake': true|false}; "
        "if null, CLI option or default is used",
    )

    # ---- derived / validation helpers ----

    @field_validator("quiet_hours")
    @classmethod
    def validate_quiet(cls, v: QuietHours | None) -> QuietHours | None:  # noqa: D401
        """Ensure quiet_hours.start != quiet_hours.end."""
        if v and v.start == v.end:
            raise ValueError("quiet_hours start and end cannot be identical")
        return v


def load_config(path: Path) -> WeatherConfig:
    """Parse and validate a YAML config file."""
    import yaml  # local import to avoid hard dep for callers

    try:
        data = yaml.safe_load(path.read_text())
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(f"Unable to read config YAML: {exc}") from exc

    try:
        return WeatherConfig.model_validate(data)
    except ValidationError as err:
        raise RuntimeError(f"Invalid configuration:\n{err}") from err
