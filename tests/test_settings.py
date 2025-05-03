import pytest
from datetime import datetime
from zoneinfo import ZoneInfo
from rpiweather.settings.user import UserSettings, QuietHours


def test_quiet_hours_validation_error() -> None:
    with pytest.raises(ValueError):
        QuietHours(start=6, end=6)  # start and end cannot be the same


def test_user_settings_quiet_check() -> None:
    cfg = UserSettings(
        api_key="test-key-abc",
        lat=0.0,
        lon=0.0,
        city="Nowhere",
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
        stay_awake_url=None,
        hourly_count=6,
        daily_count=5,
        quiet_hours=QuietHours(start=22, end=6),
    )
    quiet_time = datetime(2025, 5, 3, 3, 0, tzinfo=ZoneInfo("UTC"))
    not_quiet = datetime(2025, 5, 3, 14, 0, tzinfo=ZoneInfo("UTC"))
    assert cfg.is_quiet_time(quiet_time) is True
    assert cfg.is_quiet_time(not_quiet) is False


def test_user_settings_format_time() -> None:
    cfg = UserSettings(
        api_key="test-key-abc",
        lat=0.0,
        lon=0.0,
        city="Nowhere",
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
        timezone="America/New_York",
        stay_awake_url=None,
        hourly_count=6,
        daily_count=5,
    )
    dt = datetime(2025, 5, 3, 14, 30)
    formatted = cfg.format_time(dt)
    assert formatted.endswith("PM")
    assert ":" in formatted


def test_user_settings_critical_battery() -> None:
    cfg = UserSettings(
        api_key="test-key-abc",
        lat=0.0,
        lon=0.0,
        city="Nowhere",
        units="imperial",
        refresh_minutes=60,
        display_width=800,
        display_height=600,
        vcom_volts=-1.5,
        poweroff_soc=15,
        time_format_general="%I:%M %p",
        time_format_hourly="%I %p",
        time_format_daily="%a",
        time_format_full_date="%A, %B %d",
        timezone="UTC",
        stay_awake_url=None,
        hourly_count=6,
        daily_count=5,
    )
    assert cfg.is_critical_battery(10) is True
    assert cfg.is_critical_battery(20) is False
