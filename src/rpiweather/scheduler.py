import time
import logging
from datetime import datetime, timedelta
from typing import Optional, TYPE_CHECKING

from rpiweather.constants import DEFAULT_STAY_AWAKE_URL, FULL_REFRESH_INTERVAL
from rpiweather.helpers import QuietHoursHelper, PowerManager
from rpiweather.remote import should_stay_awake
from rpiweather.power import schedule_wakeup, graceful_shutdown

if TYPE_CHECKING:
    from rpiweather.cli import WeatherDisplay

logger = logging.getLogger("rpiweather")


class Scheduler:
    """Encapsulates the main fetch→render→display loop with power management."""

    def __init__(
        self,
        display: "WeatherDisplay",
        stay_awake_url: Optional[str] = None,
    ) -> None:
        # Use CLI default if not provided
        self.stay_awake_url = stay_awake_url or DEFAULT_STAY_AWAKE_URL
        self.display = display
        self.config = display.config

    def run(
        self, preview: bool = False, serve: bool = False, once: bool = False
    ) -> None:
        """Run the weather display loop until exit conditions are met."""
        base_minutes = self.config.refresh_minutes

        # Helper instances
        quiet_helper = QuietHoursHelper(self.config.quiet_hours)
        power_manager = PowerManager(self.config)

        while True:
            now = datetime.now()

            # Remote override of quiet hours
            if should_stay_awake(self.stay_awake_url):
                logger.debug("Stay-awake flag true - overriding quiet hours")
                in_quiet = False
            else:
                in_quiet = quiet_helper.is_quiet(now)

            if in_quiet:
                secs = quiet_helper.seconds_until_end(now)
                logger.info(
                    "Quiet hours active → sleeping %d min until %s",
                    secs // 60,
                    (now + timedelta(seconds=secs)).strftime("%H:%M"),
                )
                time.sleep(secs)
                continue

            full_refresh = (
                datetime.now() - self.display.last_full_refresh > FULL_REFRESH_INTERVAL
            )

            ok = self.display.fetch_and_render(preview, full_refresh, serve, once)

            if ok:
                self.display.error_streak = 0
                if full_refresh:
                    self.display.last_full_refresh = datetime.now()
            else:
                self.display.error_streak += 1
                if self.display.error_streak >= 3:
                    logger.warning("3 consecutive failures → backing off x4 interval")
                    time.sleep(base_minutes * 4 * 60)
                    continue

            if once:
                break

            soc, _, _ = self.display.get_battery_status()
            sleep_min = power_manager.get_refresh_delay(base_minutes, soc)

            if power_manager.should_power_off(soc, now):
                wake_dt = datetime.now() + timedelta(minutes=sleep_min)
                schedule_wakeup(wake_dt)
                logger.info(
                    "Powering off for %d min (SOC %d%%) → wake at %s",
                    sleep_min,
                    soc,
                    wake_dt.strftime("%H:%M"),
                )
                graceful_shutdown()
                break

            logger.info(
                "Battery %02d%% → sleeping %d min (%.1fx normal)",
                soc,
                sleep_min,
                sleep_min / base_minutes,
            )
            time.sleep(sleep_min * 60)
