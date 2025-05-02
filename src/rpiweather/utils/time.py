# src/rpiweather/utils/time.py
"""Time and date handling utilities."""

from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo


class TimeUtils:
    """Utilities for date and time operations."""

    @staticmethod
    def to_local_datetime(timestamp: int, timezone_name: str = "UTC") -> datetime:
        """Convert POSIX timestamp to local datetime.

        Args:
            timestamp: POSIX timestamp
            timezone_name: Timezone name

        Returns:
            Localized datetime object
        """
        return datetime.fromtimestamp(timestamp, tz=ZoneInfo(timezone_name))

    @staticmethod
    def format_datetime(dt: datetime, format_string: str) -> str:
        """Format datetime with specified format string.

        Args:
            dt: Datetime to format
            format_string: strftime format string

        Returns:
            Formatted datetime string
        """
        return dt.strftime(format_string)

    @staticmethod
    def get_time_difference_string(start: datetime, end: datetime) -> str:
        """Get human-readable time difference between two datetimes.

        Args:
            start: Starting datetime
            end: Ending datetime

        Returns:
            Formatted time difference (e.g., "2h 30m")
        """
        seconds = (end - start).total_seconds()
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"

    @staticmethod
    def now_localized() -> datetime:
        """Get current datetime with local timezone.

        Returns:
            Current datetime with local timezone
        """
        return datetime.now(timezone.utc).astimezone()
