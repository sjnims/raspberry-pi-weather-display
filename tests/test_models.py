"""Unit tests for the WeatherResponse Pydantic model and build_context helper."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, cast
import pytest

from rpiweather.weather.api import build_context
from rpiweather.weather.models import WeatherResponse

# Path to fixture JSON
FIXTURE = Path(__file__).parent / "data" / "onecall_sample.json"
SAMPLE_JSON = FIXTURE.read_text()


@pytest.fixture
def weather_response() -> WeatherResponse:
    """Fixture for a WeatherResponse instance."""
    return WeatherResponse.model_validate_json(SAMPLE_JSON)


def test_weather_response_validation(weather_response: WeatherResponse) -> None:
    """WeatherResponse should parse the OneCall sample without errors."""
    wx = weather_response

    # Basic sanity checks
    assert wx.lat
    assert wx.current.temp is not None
    assert wx.hourly, "hourly forecast list should not be empty"
    assert wx.daily, "daily forecast list should not be empty"


def test_build_context_basic(weather_response: WeatherResponse) -> None:
    """build_context returns expected keys for template rendering."""
    wx = weather_response

    cfg = {
        "lat": wx.lat,
        "lon": wx.lon,
        "city": "Testville",
        "units": "imperial",
        "time_24h": False,
        "hourly_count": 6,
        "daily_count": 3,
    }

    ctx = build_context(cast(Dict[str, Any], cfg), wx)

    required_keys = {
        "date",
        "current",
        "hourly",
        "daily",
        "sunrise",
        "sunset",
        "uvi_max",
        "aqi",
    }
    missing = required_keys - ctx.keys()
    assert not missing, f"Context missing keys: {missing}"
