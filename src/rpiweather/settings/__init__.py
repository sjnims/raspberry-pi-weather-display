"""Application settings management.

This package provides:
- UserSettings: User-configurable settings loaded from config.yaml
- ApplicationSettings: Internal application settings and defaults
"""

from .application import (
    ApplicationSettings,
    AppPaths,
    FormatAdapter,
    RefreshMode,
    RefreshSettings,
    StayAwakeURL,
)
from .user import QuietHours, UserSettings

__all__ = [
    "AppPaths",
    "ApplicationSettings",
    "FormatAdapter",
    "QuietHours",
    "RefreshMode",
    "RefreshSettings",
    "StayAwakeURL",
    "UserSettings",
]
