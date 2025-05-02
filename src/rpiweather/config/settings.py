# src/rpiweather/config/settings.py
"""Centralized application settings."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from rpiweather.config import WeatherConfig


@dataclass
class AppPaths:
    """Application paths."""

    config_file: Path
    templates_dir: Path
    static_dir: Path
    icons_map_file: Path

    @classmethod
    def from_base_dir(cls, base_dir: Path) -> "AppPaths":
        """Create paths from base directory."""
        return cls(
            config_file=base_dir / "config.yaml",
            templates_dir=base_dir / "templates",
            static_dir=base_dir / "static",
            icons_map_file=base_dir / "owm_icon_map.csv",
        )


@dataclass
class DateTimeFormats:
    """Date and time format strings."""

    general: str = "%-I:%M %p"
    hourly: str = "%-I %p"
    daily: str = "%a"
    full_date: str = "%A, %B %-d"


class Settings:
    """Application settings container."""

    def __init__(
        self,
        config: WeatherConfig,
        paths: Optional[AppPaths] = None,
        formats: Optional[DateTimeFormats] = None,
    ):
        """Initialize settings with configuration sources."""
        self.config = config
        self.paths = paths or AppPaths.from_base_dir(Path.cwd())
        self.formats = formats or DateTimeFormats()

        # Import format strings from config if available
        if hasattr(config, "time_format_general"):
            self.formats.general = config.time_format_general

        if hasattr(config, "time_format_hourly"):
            self.formats.hourly = config.time_format_hourly
