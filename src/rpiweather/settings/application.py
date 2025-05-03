"""Internal application settings derived from user settings."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Optional
from enum import Enum

from rpiweather.settings.user import UserSettings


class RefreshMode(Enum):
    """Enum for e-paper refresh modes."""

    FULL = 0  # full white-black-white refresh
    GREYSCALE = 2  # 16-level greyscale refresh (GC16)


@dataclass
class AppPaths:
    """Application paths."""

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
    """Adapter for date and time formats from user settings."""

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
    """E-ink display refresh settings."""

    full_refresh_interval: timedelta = timedelta(hours=6)
    min_shutdown_sleep_minutes: int = 20


@dataclass
class StayAwakeURL:
    """URL for remote stay-awake flag."""

    url: str = "http://localhost:8000/stay_awake.json"


class ApplicationSettings:
    """Application settings container.

    These settings combine user preferences with application defaults and derived values.
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
