"""Power-management helpers (shutdown & PiJuice wake-up)."""

from __future__ import annotations

import logging
import subprocess
from datetime import datetime, timezone
from typing import Any, Final, Protocol, Optional, runtime_checkable, cast

logger: Final = logging.getLogger(__name__)


@runtime_checkable
class WakeupProvider(Protocol):
    """Protocol for wake-up alarm providers."""

    def set_wakeup(self, wake_time: datetime) -> bool:
        """Set a wake-up alarm.

        Args:
            wake_time: The time to wake up

        Returns:
            True if successful, False otherwise
        """
        ...


class PiJuiceWakeup:
    """PiJuice HAT wake-up implementation."""

    def set_wakeup(self, wake_time: datetime) -> bool:
        """Set PiJuice RTC wake-up alarm.

        Args:
            wake_time: The time to wake up

        Returns:
            True if successful, False otherwise
        """
        try:
            import pijuice  # type: ignore[import-not-found]

            pj = pijuice.PiJuice(1, 0x14)  # type: ignore[call-arg]
            wake_secs = self._datetime_to_epoch(wake_time)
            resp = pj.rtc.SetWakeup(wake_secs)  # type: ignore[attr-defined]

            if resp.get("error") == "NO_ERROR":  # type: ignore[attr-defined]
                logger.info("PiJuice wake-up set for %s", wake_time.isoformat())
                return True

            logger.warning("PiJuice SetWakeup error: %s", cast(Any, resp))
            return False

        except Exception as exc:
            logger.debug("PiJuice wake-up unavailable: %s", exc)
            return False

    def _datetime_to_epoch(self, dt: datetime) -> int:
        """Convert datetime to epoch seconds.

        Args:
            dt: Datetime object (assumes local timezone if not specified)

        Returns:
            Epoch seconds as integer
        """
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp())


class LinuxRTCWakeup:
    """Linux RTC wake-up implementation using /sys/class/rtc."""

    def __init__(self, rtc_path: str = "/sys/class/rtc/rtc0/wakealarm") -> None:
        """Initialize with RTC wake alarm path.

        Args:
            rtc_path: Path to the RTC wake alarm file
        """
        self.rtc_path = rtc_path

    def set_wakeup(self, wake_time: datetime) -> bool:
        """Set Linux RTC wake-up alarm.

        Args:
            wake_time: The time to wake up

        Returns:
            True if successful, False otherwise
        """
        try:
            wake_epoch = str(self._datetime_to_epoch(wake_time))
            with open(self.rtc_path, "w", encoding="utf-8") as f:
                f.write("0")  # Clear previous alarm
                f.write(wake_epoch)

            logger.info("RTC wakealarm set for %s", wake_time.isoformat())
            return True

        except Exception as exc:
            logger.warning("Failed to set RTC wakealarm: %s", exc)
            return False

    def _datetime_to_epoch(self, dt: datetime) -> int:
        """Convert datetime to epoch seconds.

        Args:
            dt: Datetime object (assumes local timezone if not specified)

        Returns:
            Epoch seconds as integer
        """
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp())


class PowerManager:
    """Manages system power operations."""

    def __init__(self, wakeup_providers: Optional[list[WakeupProvider]] = None) -> None:
        """Initialize with wake-up providers.

        Args:
            wakeup_providers: List of wake-up providers to try in order
        """
        self.wakeup_providers = wakeup_providers or [
            PiJuiceWakeup(),
            LinuxRTCWakeup(),
        ]

    def schedule_wakeup(self, wake_time: datetime) -> bool:
        """Schedule the system to wake up at the specified time.

        Tries each provider in order until one succeeds.

        Args:
            wake_time: The time to wake up

        Returns:
            True if any provider succeeded, False if all failed
        """
        for provider in self.wakeup_providers:
            if provider.set_wakeup(wake_time):
                return True

        logger.warning("All wake-up methods failed for %s", wake_time.isoformat())
        return False

    def shutdown(self) -> None:
        """Initiate system shutdown.

        Uses 'sudo shutdown -h now' command.
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


# Singleton instance for backward compatibility
_power_manager = PowerManager()


# Legacy functions for backward compatibility
def schedule_wakeup(wake: datetime) -> None:
    """Schedule the Pi to power back on at wake time."""
    _power_manager.schedule_wakeup(wake)


def graceful_shutdown() -> None:
    """Initiate system shutdown."""
    _power_manager.shutdown()
