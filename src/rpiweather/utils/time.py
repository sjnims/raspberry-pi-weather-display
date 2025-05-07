# src/rpiweather/utils/time.py
"""Time and date handling utilities."""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo


class TimeUtils:
    """Time-related utility functions.

    Centralized utilities for working with dates and times:
    - Timezone conversions
    - Datetime formatting with user preferences
    - Time difference calculations
    - Current time retrieval with proper timezone handling
    """

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
        return datetime.now(UTC).astimezone()

    @staticmethod
    def datetime_to_epoch(dt: datetime) -> int:
        """Convert datetime to epoch seconds.

        Args:
            dt: Datetime object (assumes UTC timezone if not specified)

        Returns:
            Epoch seconds as integer
        """
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return int(dt.timestamp())

    @staticmethod
    def epoch_to_datetime(timestamp: int) -> datetime:
        """Convert UNIX timestamp to UTC datetime with timezone information.

        Args:
            timestamp: UNIX timestamp (seconds since epoch)

        Returns:
            Timezone-aware datetime object in UTC
        """
        return datetime.fromtimestamp(timestamp, tz=UTC)
