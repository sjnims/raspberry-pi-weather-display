from datetime import datetime

import pytest

from rpiweather.config import QuietHours
from rpiweather.power import in_quiet_hours, seconds_until_quiet_end


# ---------------------------------------------------------------------------
# Helper to build datetime easily
def dt(hour: int, minute: int = 0) -> datetime:  # noqa: D401
    """Return a fixed-date datetime at *hour*:*minute* UTC."""
    return datetime(2025, 1, 1, hour, minute)


# ── same‑day window (01→05) ────────────────────────────────────────────────
def test_in_quiet_hours_same_day():
    q = QuietHours(start=1, end=5)
    assert in_quiet_hours(dt(2), q) is True
    assert in_quiet_hours(dt(0), q) is False
    assert in_quiet_hours(dt(5), q) is False  # end exclusive


# ── wrapping‑midnight window (22→6) ─────────────────────────────────────────
def test_in_quiet_hours_wrap_midnight():
    q = QuietHours(start=22, end=6)
    assert in_quiet_hours(dt(23), q) is True
    assert in_quiet_hours(dt(3), q) is True
    assert in_quiet_hours(dt(7), q) is False


# ── disabled (None) ────────────────────────────────────────────────────────
def test_in_quiet_hours_disabled():
    assert in_quiet_hours(dt(12), None) is False


# ── seconds_until_quiet_end ────────────────────────────────────────────────
@pytest.mark.parametrize(
    ("now_h", "start", "end", "expected"),
    [
        (2, 1, 5, 3 * 3600),  # same‑day span
        (23, 22, 6, 7 * 3600),  # wrap: 23→next 06
        (7, 22, 6, 0),  # outside window
    ],
)
def test_seconds_until_quiet_end(
    now_h: int,
    start: int,
    end: int,
    expected: int,
) -> None:
    q = QuietHours(start=start, end=end)
    assert seconds_until_quiet_end(dt(now_h), q) == expected
