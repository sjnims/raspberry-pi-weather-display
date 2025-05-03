import pytest
from rpiweather.power import BatteryManager


@pytest.mark.parametrize(
    "soc, expected",
    [
        (100, 15),  # no scaling
        (75, 15),  # still full frequency
        (50, 22),  # 15 * 1.5
        (25, 30),  # 15 * 2
        (15, 45),  # 15 * 3
        (5, 60),  # 15 * 4
        (0, 60),  # 15 * 4
    ],
)
def test_refresh_scaling_varies_by_soc(soc: int, expected: int) -> None:
    result = BatteryManager.get_refresh_delay_minutes(base_minutes=15, soc=soc)
    assert result == expected


def test_refresh_delay_extends_above_user_value() -> None:
    # SoC too high: no scaling (should return base)
    assert BatteryManager.get_refresh_delay_minutes(base_minutes=15, soc=150) == 15

    assert BatteryManager.get_refresh_delay_minutes(base_minutes=15, soc=100) == 15
    assert (
        BatteryManager.get_refresh_delay_minutes(base_minutes=15, soc=50) == 22
    )  # 1.5x
    assert BatteryManager.get_refresh_delay_minutes(base_minutes=15, soc=25) == 30  # 2x
    assert BatteryManager.get_refresh_delay_minutes(base_minutes=15, soc=15) == 45  # 3x
    assert BatteryManager.get_refresh_delay_minutes(base_minutes=15, soc=5) == 60  # 4x
    assert BatteryManager.get_refresh_delay_minutes(base_minutes=15, soc=0) == 60  # 4x

    # SoC too low with very low base: scaled but no artificial clamp
    assert BatteryManager.get_refresh_delay_minutes(base_minutes=2, soc=0) == 8  # 2 * 4
    assert BatteryManager.get_refresh_delay_minutes(base_minutes=1, soc=5) == 4  # 1 * 4
    assert BatteryManager.get_refresh_delay_minutes(base_minutes=1, soc=0) == 4
