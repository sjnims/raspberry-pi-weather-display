from collections.abc import Mapping
from typing import Any
from unittest.mock import Mock

import pytest

from rpiweather.types.weather import PrecipObj
from rpiweather.weather.utils.precipitation import PrecipitationUtils


@pytest.mark.parametrize(
    "input_data, expected",
    [
        # Valid inputs
        ({"1h": 0.2}, 0.2),
        ({"1h": "0.2"}, 0.2),
        (None, 0.0),
        ({}, 0.0),
        ({"foo": 1.0}, 0.0),
        # Invalid inputs
        ({"1h": "invalid"}, 0.0),  # Non-numeric string
        ({"1h": None}, 0.0),  # Explicit None value
        ({"1h": []}, 0.0),  # Invalid type (list)
        ({"1h": {}}, 0.0),  # Invalid type (dict)
    ],
)
def test_get_one_hour_amt(input_data: Mapping[str, Any] | None, expected: float) -> None:
    assert PrecipitationUtils.get_one_hour_amt(input_data) == expected


@pytest.mark.parametrize(
    "hour_obj, imperial, expected",
    [
        # Valid rain/snow data
        ({"rain": {"1h": 2.54}}, False, "2.54"),  # mm
        ({"rain": {"1h": 2.54}}, True, "0.1"),  # ≈ 0.1 in
        ({"snow": {"1h": 2.54}}, True, "0.1"),  # fallback to snow
        ({"rain": {"1h": 0}}, True, ""),  # zero precip = ""
        ({"rain": {"1h": 0.0}}, False, ""),  # zero precip = ""
        # Missing or empty data
        ({"rain": {}}, False, ""),  # Empty rain data
        ({"snow": {}}, True, ""),  # Empty snow data
        ({"other": {"1h": 1.0}}, False, ""),  # No rain or snow key
        ({}, True, ""),  # Completely empty object
        # Large values
        ({"rain": {"1h": 1000.0}}, False, "1000.00"),  # Large mm value
        ({"rain": {"1h": 1000.0}}, True, "39.37"),  # Large value in inches
        # Edge cases for imperial conversion
        ({"rain": {"1h": 25.4}}, True, "1"),  # Exactly 1 inch
        ({"rain": {"1h": 0.254}}, True, "0.01"),  # Small value
        ({"rain": {"1h": 0.0254}}, True, "0"),  # Rounds to 0
        # PrecipObj inputs
        (Mock(rain={"1h": 2.54}, snow=None), False, "2.54"),  # mm
        (Mock(rain=None, snow={"1h": 2.54}), True, "0.1"),  # inches
        (Mock(rain=None, snow=None), False, ""),  # No precipitation
    ],
)
def test_hourly_precip(
    hour_obj: Mapping[str, Any] | PrecipObj, imperial: bool, expected: str
) -> None:
    result = PrecipitationUtils.hourly_precip(hour_obj, imperial=imperial)
    assert result == expected


@pytest.mark.parametrize(
    "hour_obj, imperial, expected",
    [
        (Mock(rain={"1h": "invalid"}, snow=None), False, ""),  # Invalid rain value
        (Mock(rain=None, snow={"1h": "invalid"}), True, ""),  # Invalid snow value
        (Mock(rain=None, snow=None), False, ""),  # No precipitation
    ],
)
def test_hourly_precip_invalid_precip_obj(
    hour_obj: PrecipObj, imperial: bool, expected: str
) -> None:
    result = PrecipitationUtils.hourly_precip(hour_obj, imperial=imperial)
    assert result == expected
