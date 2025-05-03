"""Tests for weather data models and response parsing.

These tests verify that:
1. Sample JSON responses from OpenWeather can be parsed correctly
2. Model validation catches malformed responses
3. Optional fields are handled properly
4. Timezone conversions work as expected
"""

import pytest
from typing import Any
from pydantic import ValidationError
from pathlib import Path

from rpiweather.weather.api import WeatherAPI
from rpiweather.weather.models import WeatherResponse
from rpiweather.settings import UserSettings


@pytest.fixture
def dummy_config(weather_response: WeatherResponse) -> UserSettings:
    """Fixture for a dummy UserSettings instance."""
    return UserSettings(
        lat=weather_response.lat,
        lon=weather_response.lon,
        city="Testville",
        api_key="DUMMYKEY1234567890",
        units="imperial",
        timezone="America/New_York",
        time_format_general="%-I:%M %p",
        time_format_hourly="%-I %p",
        time_format_daily="%a",
        time_format_full_date="%A, %B %-d",
        hourly_count=6,
        daily_count=3,
        refresh_minutes=120,
        display_width=800,
        display_height=480,
        poweroff_soc=20,
        stay_awake_url="",
        vcom_volts=-1.45,
    )


# Fixture for malformed JSON (missing required "lat" field)
@pytest.fixture
def bad_weather_json() -> str:
    """Return OneCall sample with a required field removed (lat)."""
    import json

    path = Path("tests/data/onecall_sample.json")
    bad_data: dict[str, Any] = json.loads(path.read_text())
    bad_data.pop("lat", None)  # remove required field
    return json.dumps(bad_data)


def test_weather_response_validation(weather_response: WeatherResponse) -> None:
    """WeatherResponse should parse the OneCall sample without errors."""
    wx = weather_response

    # Basic sanity checks
    assert wx.lat
    assert wx.current.temp is not None
    assert wx.hourly, "hourly forecast list should not be empty"
    assert wx.daily, "daily forecast list should not be empty"


# Test for validation error when required fields are missing


def test_weather_response_validation_error(bad_weather_json: str) -> None:
    """WeatherResponse should raise if required fields are missing."""
    with pytest.raises(ValidationError):
        WeatherResponse.model_validate_json(bad_weather_json)


def test_build_context_basic(
    weather_response: WeatherResponse, dummy_config: UserSettings
) -> None:
    """build_context returns expected keys for template rendering."""
    wx = weather_response

    ctx = WeatherAPI(dummy_config).build_context(wx)
    assert "date" in ctx  # basic sanity check so ctx is used


@pytest.mark.parametrize(
    "ctx_key",
    [
        "date",
        "current",
        "hourly",
        "daily",
        "sunrise",
        "sunset",
        "uvi_max",
        "aqi",
    ],
)
def test_build_context_contains_key(
    weather_response: WeatherResponse, dummy_config: UserSettings, ctx_key: str
) -> None:
    """Each expected key should be present in the build_context output."""
    ctx = WeatherAPI(dummy_config).build_context(weather_response)
    assert ctx_key in ctx
