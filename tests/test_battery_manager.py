import pytest
from datetime import datetime
from rpiweather.power import BatteryManager
from rpiweather.settings.user import UserSettings
from rpiweather.settings.user import QuietHours


@pytest.mark.parametrize(
    "soc, now, expected",
    [
        (100, datetime(2025, 5, 3, 14, 0), False),  # high SoC, normal hours
        (9, datetime(2025, 5, 3, 14, 0), True),  # low SoC, normal hours
        (10, datetime(2025, 5, 3, 14, 0), True),  # edge SoC triggers poweroff
        (8, datetime(2025, 5, 3, 3, 30), True),  # low SoC + quiet hour
        (50, datetime(2025, 5, 3, 3, 30), True),  # quiet hour only
    ],
)
def test_should_power_off_logic(soc: int, now: datetime, expected: bool) -> None:
    config = UserSettings(
        api_key="test-key-123",
        lat=0.0,
        lon=0.0,
        city="Test City",
        units="imperial",
        refresh_minutes=60,
        display_width=1872,
        display_height=1404,
        vcom_volts=-2.0,
        poweroff_soc=10,
        time_format_general="%I:%M %p",
        time_format_hourly="%I %p",
        time_format_daily="%a",
        time_format_full_date="%A, %B %d",
        timezone="UTC",
        stay_awake_url=None,
        hourly_count=3,
        daily_count=2,
        quiet_hours=QuietHours(start=2, end=6),
    )
    bm = BatteryManager(config)
    assert bm.should_power_off(soc=soc, now=now) is expected
