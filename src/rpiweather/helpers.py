"""General helper utilities shared across rpiweather packages."""

from __future__ import annotations

from datetime import datetime, time, timedelta
from typing import Optional

from rpiweather.config import QuietHours

__all__ = ["in_quiet_hours", "seconds_until_quiet_end"]


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
