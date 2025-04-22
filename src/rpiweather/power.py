"""Power-management helpers (shutdown & PiJuice wake-up)."""

from __future__ import annotations

import logging
import subprocess
from datetime import datetime, timezone
from typing import Any, Final, cast

logger: Final = logging.getLogger(__name__)

# ---------------------------------------------------------------------------


def _epoch_for(dt: datetime) -> int:
    """Return epoch seconds for *dt* (assumed local-tz or UTC)."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp())


def _set_pijuice_alarm(wake: datetime) -> bool:
    """
    Try to program PiJuice RTC wake-up alarm.

    Returns **True** on success, **False** on any failure.
    """
    try:
        import pijuice  # type: ignore[import-not-found]

        pj = pijuice.PiJuice(1, 0x14)  # type: ignore[call-arg]
        wake_secs = _epoch_for(wake)
        resp = pj.rtc.SetWakeup(wake_secs)  # type: ignore[attr-defined]
        if resp.get("error") == "NO_ERROR":  # type: ignore[attr-defined]
            logger.info("PiJuice wake-up set for %s", wake.isoformat())
            return True
        logger.warning("PiJuice SetWakeup error: %s", cast(Any, resp))
        return False
    except Exception as exc:
        logger.debug("PiJuice wake-up unavailable: %s", exc)
        return False


# ---------------------------------------------------------------------------


def schedule_wakeup(wake: datetime) -> None:
    """
    Schedule the Pi to power back on at *wake*.

    • Attempts PiJuice first.
    • Fallback is RPi RTC (wakealarm in /sys/class/rtc/rtc0) if running on Linux.
    """
    if _set_pijuice_alarm(wake):
        return

    # Fallback: write to /sys wakealarm (Linux only)
    try:
        wake_epoch = str(_epoch_for(wake))
        with open("/sys/class/rtc/rtc0/wakealarm", "w", encoding="utf-8") as f:
            f.write("0")  # clear previous alarm
            f.write(wake_epoch)
        logger.info("RTC wakealarm set for %s", wake.isoformat())
    except Exception as exc:
        logger.warning("Failed to set RTC wakealarm: %s", exc)


def graceful_shutdown() -> None:
    """
    Initiate system shutdown.

    Uses `sudo shutdown -h now`; if that fails in dev environment,
    logs a warning but does not raise.
    """
    try:
        subprocess.run(
            ["sudo", "shutdown", "-h", "now"],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        logger.warning("Shutdown command failed: %s", exc)
    except FileNotFoundError:
        logger.warning("Shutdown command not found (dev environment)")
