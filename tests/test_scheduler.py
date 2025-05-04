import pytest

from pytest import MonkeyPatch
from datetime import datetime, timedelta
from unittest.mock import Mock
from zoneinfo import ZoneInfo

from rpiweather.scheduler import Scheduler
from rpiweather.settings import UserSettings, QuietHours


# Fixture to provide a UserSettings config object for tests
@pytest.fixture
def config() -> UserSettings:
    return UserSettings(
        api_key="test-key-abc",
        lat=0.0,
        lon=0.0,
        city="Test City",
        units="imperial",
        refresh_minutes=60,
        display_width=800,
        display_height=600,
        vcom_volts=-1.5,
        poweroff_soc=10,
        time_format_general="%I:%M %p",
        time_format_hourly="%I %p",
        time_format_daily="%a",
        time_format_full_date="%A, %B %d",
        timezone="UTC",
        stay_awake_url="http://localhost/fake_wake.json",
        hourly_count=6,
        daily_count=5,
        quiet_hours=QuietHours(start=2, end=6),
    )


def fake_create_wake_state_provider(_: object) -> object:
    class FakeWakeProvider:
        def should_stay_awake(self) -> bool:
            return False

    return FakeWakeProvider()


def fake_is_not_quiet(_: object, __: object) -> bool:
    return False


def fake_seconds_until_end(_: object, __: object) -> int:
    return 1800


def should_power_off(_: object, __: int, ___: object) -> bool:
    return True


def noop_sleep(_: float) -> None:
    return None


def test_scheduler_triggers_shutdown(
    monkeypatch: MonkeyPatch, config: UserSettings
) -> None:
    display = Mock()

    was_shutdown = {"called": False}

    def record_shutdown() -> None:
        print("!!! SHUTDOWN CALLBACK INVOKED !!!")
        was_shutdown["called"] = True

    scheduler = Scheduler(display, shutdown_callback=record_shutdown)

    # Patch required behaviors
    display.last_full_refresh = datetime.now(ZoneInfo("UTC")) - timedelta(hours=13)
    scheduler.config = config
    scheduler.stay_awake_url = config.stay_awake_url or ""

    monkeypatch.setattr(
        "rpiweather.scheduler.create_wake_state_provider",
        fake_create_wake_state_provider,
    )
    monkeypatch.setattr(
        "rpiweather.scheduler.QuietHoursHelper.is_quiet", fake_is_not_quiet
    )
    monkeypatch.setattr(
        "rpiweather.scheduler.QuietHoursHelper.seconds_until_end",
        fake_seconds_until_end,
    )
    monkeypatch.setattr(
        "rpiweather.scheduler.BatteryManager.should_power_off", should_power_off
    )

    display.fetch_and_render = Mock(return_value=True)
    display.get_battery_status = Mock(return_value=(5, 0, False))

    def mock_schedule_wakeup(self: object, wake_time: datetime) -> bool:
        return True

    monkeypatch.setattr(
        "rpiweather.power.PowerManager.schedule_wakeup",
        mock_schedule_wakeup,
    )

    import time

    original_sleep = time.sleep
    time.sleep = noop_sleep
    try:
        scheduler.run(preview=False, serve=False, once=False)
    finally:
        time.sleep = original_sleep

    assert was_shutdown["called"]
