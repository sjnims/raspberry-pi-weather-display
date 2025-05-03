import pytest
import json
from pathlib import Path
from rpiweather.weather.models import WeatherResponse


@pytest.fixture
def weather_response() -> WeatherResponse:
    path = Path("tests/data/onecall_sample.json")
    raw = json.loads(path.read_text())
    return WeatherResponse.model_validate(raw)
