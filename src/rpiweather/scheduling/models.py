"""Data models for scheduling and refresh settings."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta


@dataclass
class RefreshSettings:
    """E-ink display refresh settings."""

    full_refresh_interval: timedelta = timedelta(hours=6)


@dataclass
class StayAwakeURL:
    """Remote stay-awake control endpoint configuration."""

    url: str = "http://localhost:8000/stay_awake.json"
