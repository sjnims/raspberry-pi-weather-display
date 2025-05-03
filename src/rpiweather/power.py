"""Power-management helpers (shutdown & PiJuice wake-up)."""

from __future__ import annotations

import logging
import subprocess
from datetime import datetime, timedelta, timezone
from typing import Any, Final, Protocol, Optional, runtime_checkable, cast

from rpiweather.settings import QuietHours, UserSettings

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


# ── Battery & Quiet-Hours Policy ──────────────────────────────────────────────
class BatteryManager:
    """Manages battery-specific logic for refresh timing and power decisions."""

    def __init__(self, config: UserSettings) -> None:
        """Initialize the battery manager with configuration.

        Args:
            config: Weather display configuration
        """
        self.config = config

    @staticmethod
    def get_refresh_delay_minutes(base_minutes: int, soc: int) -> int:
        """Calculate adaptive refresh delay based on battery level."""
        if soc <= 5:
            return base_minutes * 4
        elif soc <= 15:
            return base_minutes * 3
        elif soc <= 25:
            return base_minutes * 2
        elif soc <= 50:
            return int(base_minutes * 1.5)
        return base_minutes

    def should_power_off(self, soc: int, now: datetime) -> bool:
        """Determine if system should power off based on battery and time."""
        # Use self.config instead of passing cfg parameter
        if soc <= self.config.poweroff_soc:
            return True

        # Quiet hours override
        if self.config.quiet_hours and QuietHoursHelper(
            self.config.quiet_hours
        ).is_quiet(now):
            return True

        return False


class QuietHoursManager:
    """Manages quiet hours timing calculations."""

    @staticmethod
    def seconds_until_quiet_end(ts: datetime, quiet: Optional[QuietHours]) -> int:
        """Calculate seconds until quiet hours end."""
        if not quiet:
            return 0

        current_hour = ts.hour
        start = quiet.start
        end = quiet.end

        # If not in quiet hours now, return 0
        if start < end:
            if not (start <= current_hour < end):
                return 0
            end_dt = ts.replace(hour=end, minute=0, second=0, microsecond=0)
        else:
            # wrapping interval
            if not (current_hour >= start or current_hour < end):
                return 0
            # if before midnight segment
            if current_hour >= start:
                base = ts
            else:
                base = ts - timedelta(days=1)
            end_dt = base.replace(
                hour=end, minute=0, second=0, microsecond=0
            ) + timedelta(days=1)

        return int((end_dt - ts).total_seconds())


class QuietHoursHelper:
    """Encapsulates quiet hours configuration and operations."""

    def __init__(self, quiet: Optional[QuietHours]) -> None:
        self._quiet = quiet

    def is_quiet(self, ts: datetime) -> bool:
        """Return True if ts falls within the configured quiet hours."""
        if not self._quiet:
            return False

        current_hour = ts.hour
        start = self._quiet.start
        end = self._quiet.end

        # Non-wrapping interval
        if start < end:
            return start <= current_hour < end
        # Wrapping interval
        return current_hour >= start or current_hour < end

    def seconds_until_end(self, ts: datetime) -> int:
        """Return seconds until quiet hours end, or 0 if not in quiet hours."""
        return QuietHoursManager.seconds_until_quiet_end(ts, self._quiet)
