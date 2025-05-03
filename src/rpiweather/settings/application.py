"""Internal application settings derived from user settings."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Optional
from enum import Enum

from rpiweather.settings.user import UserSettings


class RefreshMode(Enum):
    """Display refresh modes for e-paper displays.

    Different refresh modes offer tradeoffs between image quality, refresh speed,
    and power consumption. The optimal mode depends on display content and
    battery considerations.
    """

    FULL = 0  # Full white-black-white refresh (highest quality, slowest)
    GREYSCALE = 2  # 16-level greyscale refresh (GC16, balanced mode)


@dataclass
class AppPaths:
    """Application file and directory paths.

    Centralizes all path configurations for the application, including
    template locations, static assets, configuration files, and
    output directories.

    Using a dedicated class for paths makes it easier to implement
    features that depend on filesystem layout, such as preview generation
    or icon mapping.
    """

    config_file: Path
    templates_dir: Path
    static_dir: Path
    icons_map_file: Path
    preview_dir: Path
    preview_html: str = "dash-preview.html"
    preview_png: str = "dash-preview.png"

    @classmethod
    def from_base_dir(cls, base_dir: Path) -> "AppPaths":
        """Create paths from base directory."""
        return cls(
            config_file=base_dir / "config.yaml",
            templates_dir=base_dir / "templates",
            static_dir=base_dir / "static",
            icons_map_file=base_dir / "owm_icon_map.csv",
            preview_dir=base_dir / "preview",
        )


class FormatAdapter:
    """Adapter for date and time formats from user settings.

    This class provides a clean interface to access date/time format strings,
    isolating the rest of the application from the specific structure of
    UserSettings. All format strings come from user configuration.
    """

    def __init__(self, user_settings: UserSettings):
        """Initialize with user settings."""
        self._user = user_settings

    @property
    def general(self) -> str:
        """General time format."""
        return self._user.time_format_general

    @property
    def hourly(self) -> str:
        """Hourly forecast time format."""
        return self._user.time_format_hourly

    @property
    def daily(self) -> str:
        """Daily forecast date format."""
        return self._user.time_format_daily

    @property
    def full_date(self) -> str:
        """Full date format."""
        return self._user.time_format_full_date


@dataclass
class RefreshSettings:
    """E-ink display refresh settings.

    Controls how frequently the display performs full refreshes versus partial
    refreshes, and defines minimum sleep durations between refresh cycles.

    Full refreshes clear ghosting artifacts but take longer and use more power.
    """

    full_refresh_interval: timedelta = timedelta(hours=6)
    min_shutdown_sleep_minutes: int = 20


@dataclass
class StayAwakeURL:
    """Remote stay-awake control endpoint configuration.

    The application can optionally check a remote URL that returns
    a JSON response with an "awake" flag. This allows for external
    control of the device's sleep behavior.

    Example response: {"awake": true}
    """

    url: str = "http://localhost:8000/stay_awake.json"


class ApplicationSettings:
    """Application settings container.

    This class combines user-provided configuration with application defaults
    to create a complete settings object for the weather display. It handles:

    - Path configuration (templates, static files, output)
    - Date and time formatting through FormatAdapter
    - Display settings (dimensions, refresh modes)
    - Refresh timing and power management

    The class uses composition to maintain separation of concerns, with specialized
    adapters for different setting types.

    Examples:
        # Basic usage
        user_settings = UserSettings.load()
        app_settings = ApplicationSettings(user_settings)

        # Access derived settings
        template_path = app_settings.paths.templates_dir
        date_format = app_settings.formats.full_date
    """

    def __init__(
        self,
        user_settings: UserSettings,
        paths: Optional[AppPaths] = None,
        formats: Optional[FormatAdapter] = None,
        refresh: Optional[RefreshSettings] = None,
        stay_awake_url: Optional[StayAwakeURL] = None,
        refresh_mode: Optional[RefreshMode] = None,
    ):
        """Initialize application settings with configuration sources."""
        self.user = user_settings  # Store user settings directly
        self.paths = paths or AppPaths.from_base_dir(Path(__file__).parents[3])
        self.formats = formats or FormatAdapter(user_settings)
        self.refresh = refresh or RefreshSettings()
        self.stay_awake_url = stay_awake_url or StayAwakeURL()
        self.refresh_mode = refresh_mode or RefreshMode.GREYSCALE
