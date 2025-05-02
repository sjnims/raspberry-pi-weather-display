"""General helper utilities shared across rpiweather packages."""

from __future__ import annotations

from datetime import datetime, time, timedelta
from typing import Optional

from rpiweather.config import QuietHours, WeatherConfig


class BatteryManager:
    """Manages battery-specific logic for refresh timing and power decisions."""

    @staticmethod
    def get_refresh_delay_minutes(base_minutes: int, soc: int) -> int:
        """Calculate adaptive refresh delay based on battery level.

        Args:
            base_minutes: Base refresh interval in minutes
            soc: Battery state of charge percentage

        Returns:
            Adjusted refresh interval in minutes
        """
        if soc <= 5:
            return base_minutes * 4
        elif soc <= 15:
            return base_minutes * 3
        elif soc <= 25:
            return base_minutes * 2
        elif soc <= 50:
            return int(base_minutes * 1.5)
        return base_minutes

    @staticmethod
    def should_power_off(cfg: WeatherConfig, soc: int, now: datetime) -> bool:
        """Determine if system should power off based on battery and time.

        Args:
            cfg: Weather display configuration
            soc: Battery state of charge percentage
            now: Current time

        Returns:
            True if system should power off
        """
        # Critical battery level
        if soc <= cfg.poweroff_soc:
            return True

        # Quiet hours (using QuietHours from config directly)
        if cfg.quiet_hours and in_quiet_hours(now, cfg.quiet_hours):
            return True

        return False


class QuietHoursManager:
    """Manages quiet hours timing calculations."""

    @staticmethod
    def seconds_until_quiet_end(ts: datetime, quiet: Optional[QuietHours]) -> int:
        """Calculate seconds until quiet hours end.

        Args:
            ts: Current timestamp
            quiet: Quiet hours configuration

        Returns:
            Seconds until quiet hours end, or 0 if not in quiet hours
        """
        if not quiet or not in_quiet_hours(ts, quiet):
            return 0

        end_time = time(quiet.end)
        candidate = ts.replace(hour=end_time.hour, minute=0, second=0, microsecond=0)
        if candidate <= ts:
            candidate += timedelta(days=1)

        return int((candidate - ts).total_seconds())


class QuietHoursHelper:
    """Encapsulates quiet hours configuration and operations."""

    def __init__(self, quiet: Optional[QuietHours]) -> None:
        self._quiet = quiet

    def is_quiet(self, ts: datetime) -> bool:
        """Return True if *ts* is within the configured quiet hours."""
        return in_quiet_hours(ts, self._quiet)

    def seconds_until_end(self, ts: datetime) -> int:
        """Return seconds until quiet hours end, or 0 if not in quiet hours."""
        return QuietHoursManager.seconds_until_quiet_end(ts, self._quiet)


class PowerManager:
    """Encapsulates battery refresh delay and power-off logic based on config."""

    def __init__(self, cfg: WeatherConfig) -> None:
        self._cfg = cfg

    def get_refresh_delay(self, base_minutes: int, soc: int) -> int:
        """Return adjusted refresh interval based on battery SoC."""
        return BatteryManager.get_refresh_delay_minutes(base_minutes, soc)

    def should_power_off(self, soc: int, now: datetime) -> bool:
        """Return True if the system should power off now."""
        return BatteryManager.should_power_off(self._cfg, soc, now)


# Legacy functions for backward compatibility
def in_quiet_hours(ts: datetime, quiet: Optional[QuietHours]) -> bool:
    """Return ``True`` if *ts* falls inside the user-defined quiet-hour window.

    • If ``quiet`` is *None* → always returns ``False``.
    • If ``start < end`` (e.g. 22 → 6) window **wraps midnight**.
    • If ``start < end`` (e.g. 1 → 5) window is within the same day.

    Note: Consider using quiet.is_quiet_time() directly from QuietHours.
    """
    if not quiet:
        return False

    # Use QuietHours method if available - otherwise fall back to old logic
    if hasattr(quiet, "is_quiet_time"):
        return quiet.is_quiet_time(ts)

    start = time(quiet.start)
    end = time(quiet.end)

    if start < end:  # simple span within same day
        return start <= ts.time() < end

    # window wraps midnight (e.g. 22 → 6)
    return ts.time() >= start or ts.time() < end


def seconds_until_quiet_end(ts: datetime, quiet: Optional[QuietHours]) -> int:
    """If *ts* is inside quiet hours, return seconds until the window ends.
    Otherwise return 0.
    """
    return QuietHoursManager.seconds_until_quiet_end(ts, quiet)


def get_refresh_delay_minutes(base_minutes: int, soc: int) -> int:
    """Return the refresh delay in minutes based on the battery state of charge (SoC).
    Slows down refresh rate as battery level drops to conserve power.
    """
    return BatteryManager.get_refresh_delay_minutes(base_minutes, soc)


def should_power_off(cfg: WeatherConfig, soc: int, now: datetime) -> bool:
    """Return True if the system should power off based on battery SoC or quiet hours."""
    return BatteryManager.should_power_off(cfg, soc, now)


# Export legacy functions for backward compatibility
__all__ = [
    "in_quiet_hours",
    "seconds_until_quiet_end",
    "get_refresh_delay_minutes",
    "should_power_off",
    "BatteryManager",
    "QuietHoursManager",
    "QuietHoursHelper",
    "PowerManager",
]
