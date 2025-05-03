import pytest
from unittest.mock import Mock
from pytest import MonkeyPatch
from rpiweather.scheduler import Scheduler
from rpiweather.settings.user import UserSettings, QuietHours
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


def fake_seconds_until_end(_: object, __: object) -> int:
    return 0


def always_false(_: object) -> bool:
    return False


def always_true(_: object) -> bool:
    return True


def fake_is_quiet(self: object, ts: object) -> bool:
    return True


def fake_is_not_quiet(self: object, ts: object) -> bool:
    return False


def should_power_off(_: object, __: int, ___: object) -> bool:
    return True


def should_not_power_off(_: object, __: int, ___: object) -> bool:
    return False


def noop_sleep(_: float) -> None:
    return None


# Move FakeWakeProvider to module level
class FakeWakeProvider:
    def should_stay_awake(self) -> bool:
        return False


def fake_create_wake_state_provider(_: object) -> FakeWakeProvider:
    return FakeWakeProvider()


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


def test_scheduler_skips_during_quiet(
    monkeypatch: MonkeyPatch, config: UserSettings
) -> None:
    display = Mock()
    monkeypatch.setattr(
        "rpiweather.scheduler.create_wake_state_provider",
        fake_create_wake_state_provider,
    )
    scheduler = Scheduler(display)
    display.last_full_refresh = datetime.now(ZoneInfo("UTC")) - timedelta(hours=7)
    scheduler.config.quiet_hours = QuietHours(start=2, end=6)

    call_counter = {"count": 0}

    def toggle_is_quiet(_: object, __: object) -> bool:
        call_counter["count"] += 1
        return call_counter["count"] == 1

    monkeypatch.setattr(
        "rpiweather.scheduler.QuietHoursHelper.is_quiet", toggle_is_quiet
    )
    monkeypatch.setattr(
        "rpiweather.scheduler.QuietHoursHelper.seconds_until_end",
        fake_seconds_until_end,
    )

    display.fetch_and_render = Mock(return_value=True)
    import time

    original_sleep = time.sleep
    time.sleep = noop_sleep
    try:
        scheduler.config = config
        scheduler.stay_awake_url = config.stay_awake_url or ""
        scheduler.run(preview=False, serve=False, once=True)
    finally:
        time.sleep = original_sleep


def test_scheduler_triggers_shutdown(
    monkeypatch: MonkeyPatch, config: UserSettings
) -> None:
    display = Mock()
    monkeypatch.setattr(
        "rpiweather.scheduler.create_wake_state_provider",
        fake_create_wake_state_provider,
    )
    scheduler = Scheduler(display)
    display.last_full_refresh = datetime.now(ZoneInfo("UTC")) - timedelta(hours=7)

    monkeypatch.setattr(
        "rpiweather.scheduler.QuietHoursHelper.is_quiet", fake_is_not_quiet
    )
    monkeypatch.setattr(
        "rpiweather.scheduler.BatteryManager.should_power_off",
        should_power_off,
    )
    monkeypatch.setattr("rpiweather.scheduler.PowerManager.shutdown", Mock())

    display.fetch_and_render = Mock(return_value=True)
    import time

    original_sleep = time.sleep
    time.sleep = noop_sleep
    try:
        scheduler.config = config
        scheduler.stay_awake_url = config.stay_awake_url or ""
        scheduler.run(preview=False, serve=False, once=True)
    finally:
        time.sleep = original_sleep

    rpi_shutdown = pytest.importorskip("rpiweather.scheduler.PowerManager.shutdown")
    rpi_shutdown.assert_called_once()


def test_scheduler_runs_display(monkeypatch: MonkeyPatch, config: UserSettings) -> None:
    display = Mock()
    monkeypatch.setattr(
        "rpiweather.scheduler.create_wake_state_provider",
        fake_create_wake_state_provider,
    )
    scheduler = Scheduler(display)
    display.last_full_refresh = datetime.now(ZoneInfo("UTC")) - timedelta(hours=7)

    monkeypatch.setattr(
        "rpiweather.scheduler.QuietHoursHelper.is_quiet", fake_is_not_quiet
    )
    monkeypatch.setattr(
        "rpiweather.scheduler.BatteryManager.should_power_off",
        should_not_power_off,
    )

    display.fetch_and_render = Mock(return_value=True)
    import time

    original_sleep = time.sleep
    time.sleep = noop_sleep
    try:
        scheduler.config = config
        scheduler.stay_awake_url = config.stay_awake_url or ""
        scheduler.run(preview=False, serve=False, once=True)
    finally:
        time.sleep = original_sleep

    display.fetch_and_render.assert_called_once()
