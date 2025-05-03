"""Scheduler for the E-Ink Weather Display application."""

import time
import logging
from datetime import timedelta
from typing import Optional, TYPE_CHECKING

from rpiweather.settings import (
    StayAwakeURL,
    RefreshSettings,
    RefreshMode,
)
from rpiweather.remote import create_wake_state_provider
from rpiweather.power import QuietHoursHelper, PowerManager, BatteryManager
from rpiweather.utils import TimeUtils

if TYPE_CHECKING:
    from rpiweather.cli import WeatherDisplay

logger = logging.getLogger("rpiweather")


class Scheduler:
    """Manages application refresh cycles and sleep scheduling.

    Controls when the application should:
    - Refresh the display
    - Enter sleep mode to conserve power
    - Wake up for the next update
    - Stay awake based on remote configuration

    The scheduler adjusts refresh intervals based on battery status
    and can check a remote URL to determine if the device should
    stay awake.
    """

    def __init__(
        self,
        display: "WeatherDisplay",
        stay_awake_url: Optional[str] = None,
    ) -> None:
        # Display controller and config
        self.display = display
        self.config = display.config

        # Resolve stay-awake URL: CLI override → config → default
        self.stay_awake_url = (
            stay_awake_url or self.config.stay_awake_url or StayAwakeURL.url
        )

    def run(
        self,
        preview: bool = False,
        serve: bool = False,
        once: bool = False,
    ) -> None:
        """Run the weather display loop until exit conditions are met."""
        base_minutes = self.config.refresh_minutes

        # Helpers and policy managers
        quiet_helper = QuietHoursHelper(self.config.quiet_hours)
        power_manager = PowerManager()
        battery_manager = BatteryManager(self.config)

        while True:
            now = TimeUtils.now_localized()

            # Remote “stay awake” override
            wake_provider = create_wake_state_provider(self.stay_awake_url)
            if wake_provider.should_stay_awake():
                logger.debug("Stay-awake flag true → bypassing quiet hours")
                in_quiet = False
            else:
                in_quiet = quiet_helper.is_quiet(now)

            # If in quiet hours, sleep until they end
            if in_quiet:
                secs = quiet_helper.seconds_until_end(now)
                logger.info(
                    "Quiet hours active → sleeping %d min until %s",
                    secs // 60,
                    (now + timedelta(seconds=secs)).strftime("%H:%M"),
                )
                time.sleep(secs)
                continue

            # Determine if a full e-ink refresh is due
            full_refresh_needed = (
                now - self.display.last_full_refresh
                > RefreshSettings.full_refresh_interval
            )

            # Fetch data and render
            ok = self.display.fetch_and_render(
                preview,
                RefreshMode.FULL if full_refresh_needed else RefreshMode.GREYSCALE,
                serve,
                once,
            )

            if ok:
                # Reset error counter and update full-refresh timestamp
                self.display.error_streak = 0
                if full_refresh_needed:
                    self.display.last_full_refresh = TimeUtils.now_localized()
            else:
                # Increment error streak and back off if too many failures
                self.display.error_streak += 1
                if self.display.error_streak >= 3:
                    logger.warning("3 consecutive failures → backing off x4 interval")
                    time.sleep(base_minutes * 4 * 60)
                    continue

            # If running only once, exit now
            if once:
                break

            # Compute sleep interval based on battery state
            soc, _, _ = self.display.get_battery_status()
            sleep_min = battery_manager.get_refresh_delay_minutes(base_minutes, soc)

            # Handle power-off condition
            if battery_manager.should_power_off(soc, now):
                wake_dt = TimeUtils.now_localized() + timedelta(minutes=sleep_min)
                power_manager.schedule_wakeup(wake_dt)
                logger.info(
                    "Powering off for %d min (SOC %d%%) → wake at %s",
                    sleep_min,
                    soc,
                    TimeUtils.format_datetime(wake_dt, "%H:%M"),
                )
                power_manager.shutdown()
                break

            # Normal sleep
            logger.info(
                "Battery %02d%% → sleeping %d min (%.1fx normal)",
                soc,
                sleep_min,
                sleep_min / base_minutes,
            )
            time.sleep(sleep_min * 60)
