import pytest
from typing import Any, Mapping
from rpiweather.weather.utils.precipitation import PrecipitationUtils


@pytest.mark.parametrize(
    "input_data, expected",
    [
        ({"1h": 0.2}, 0.2),
        ({"1h": "0.2"}, 0.2),
        (None, 0.0),
        ({}, 0.0),
        ({"foo": 1.0}, 0.0),
    ],
)
def test_get_one_hour_amt(
    input_data: Mapping[str, Any] | None, expected: float
) -> None:
    assert PrecipitationUtils.get_one_hour_amt(input_data) == expected


@pytest.mark.parametrize(
    "hour_obj, imperial, expected",
    [
        ({"rain": {"1h": 2.54}}, False, "2.54"),  # mm
        ({"rain": {"1h": 2.54}}, True, "0.1"),  # ≈ 0.1 in
        ({"snow": {"1h": 2.54}}, True, "0.1"),  # fallback to snow
        ({"rain": {"1h": 0}}, True, ""),  # zero precip = ""
        ({"rain": {"1h": 0.0}}, False, ""),  # zero precip = ""
        ({}, False, ""),  # no rain/snow at all
    ],
)
def test_hourly_precip(
    hour_obj: Mapping[str, Any], imperial: bool, expected: str
) -> None:
    result = PrecipitationUtils.hourly_precip(hour_obj, imperial=imperial)
    assert result == expected
