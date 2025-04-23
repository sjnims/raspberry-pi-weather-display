"""Unit tests for the WeatherResponse Pydantic model and build_context helper."""

from __future__ import annotations

from pathlib import Path
import pytest
from rpiweather.weather.api import WeatherCfgDict

from rpiweather.weather.api import build_context
from rpiweather.weather.models import WeatherResponse
from typing import Any
from pydantic import ValidationError

# Path to fixture JSON
FIXTURE = Path(__file__).parent / "data" / "onecall_sample.json"
SAMPLE_JSON = FIXTURE.read_text(encoding="utf-8")


@pytest.fixture
def weather_response() -> WeatherResponse:
    """Fixture for a WeatherResponse instance."""
    return WeatherResponse.model_validate_json(SAMPLE_JSON)


# Fixture for malformed JSON (missing required "lat" field)
@pytest.fixture
def bad_weather_json() -> str:
    """Return OneCall sample with a required field removed (lat)."""
    import json

    bad_data: dict[str, "Any"] = json.loads(SAMPLE_JSON)
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


def test_build_context_basic(weather_response: WeatherResponse) -> None:
    """build_context returns expected keys for template rendering."""
    wx = weather_response

    cfg: WeatherCfgDict = {
        "lat": wx.lat,
        "lon": wx.lon,
        "api_key": "DUMMYKEY1234567890",
        "refresh_minutes": 120,
        "poweroff_soc": 10,
        "city": "Testville",
        "units": "imperial",
        "time_24h": False,
        "hourly_count": 6,
        "daily_count": 3,
    }

    ctx = build_context(cfg, wx)
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
    weather_response: WeatherResponse, ctx_key: str
) -> None:
    """Each expected key should be present in the build_context output."""
    cfg: WeatherCfgDict = {
        "lat": weather_response.lat,
        "lon": weather_response.lon,
        "api_key": "DUMMYKEY1234567890",
        "refresh_minutes": 120,
        "poweroff_soc": 10,
        "city": "Testville",
        "units": "imperial",
        "time_24h": False,
        "hourly_count": 6,
        "daily_count": 3,
    }

    ctx = build_context(cfg, weather_response)
    assert ctx_key in ctx
