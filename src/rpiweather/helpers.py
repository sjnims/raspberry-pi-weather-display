"""General helper utilities shared across rpiweather packages."""

from __future__ import annotations

from datetime import datetime, time, timedelta
from typing import Optional

from rpiweather.config import QuietHours, WeatherConfig

__all__ = ["in_quiet_hours", "seconds_until_quiet_end", "get_refresh_delay_minutes"]


def in_quiet_hours(ts: datetime, quiet: Optional[QuietHours]) -> bool:
    """
    Return ``True`` if *ts* falls inside the user-defined quiet-hour window.

    • If ``quiet`` is *None* → always returns ``False``.
    • If ``start < end`` (e.g. 22 → 6) window **wraps midnight**.
    • If ``start < end`` (e.g. 1 → 5) window is within the same day.
    """
    if not quiet:
        return False

    start = time(quiet.start)
    end = time(quiet.end)

    if start < end:  # simple span within same day
        return start <= ts.time() < end

    # window wraps midnight (e.g. 22 → 6)
    return ts.time() >= start or ts.time() < end


def seconds_until_quiet_end(ts: datetime, quiet: Optional[QuietHours]) -> int:
    """
    If *ts* is inside quiet hours, return seconds until the window ends.
    Otherwise return 0.
    """
    if not quiet or not in_quiet_hours(ts, quiet):
        return 0

    end_time = time(quiet.end)
    candidate = ts.replace(hour=end_time.hour, minute=0, second=0, microsecond=0)
    if candidate <= ts:
        candidate += timedelta(days=1)

    return int((candidate - ts).total_seconds())


def get_refresh_delay_minutes(base_minutes: int, soc: int) -> int:
    """
    Return the refresh delay in minutes based on the battery state of charge (SoC).
    Slows down refresh rate as battery level drops to conserve power.
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


def should_power_off(cfg: WeatherConfig, soc: int, now: datetime) -> bool:
    """
    Return True if the system should power off based on battery SoC or quiet hours.
    """
    if soc <= cfg.poweroff_soc:
        return True
    if in_quiet_hours(now, cfg.quiet_hours):
        return True
    return False
