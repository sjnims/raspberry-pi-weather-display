import pytest
import json
from unittest.mock import patch, Mock
from rpiweather.weather.api import WeatherAPI
from rpiweather.settings.user import UserSettings
from rpiweather.weather.models import WeatherResponse
from rpiweather.weather.errors import WeatherAPIError


@pytest.fixture
def config() -> UserSettings:
    return UserSettings(
        api_key="fake-api-key",
        lat=33.7488,
        lon=-84.3880,
        city="Atlanta",
        units="imperial",
        refresh_minutes=60,
        display_width=1872,
        display_height=1404,
        vcom_volts=-2.0,
        poweroff_soc=5,
        time_format_general="%I:%M %p",
        time_format_hourly="%I %p",
        time_format_daily="%a",
        time_format_full_date="%A, %B %d",
        timezone="America/New_York",
        stay_awake_url=None,
        hourly_count=6,
        daily_count=5,
    )


@pytest.fixture
def api(config: UserSettings) -> WeatherAPI:
    return WeatherAPI(config)


def test_fetch_weather_success(api: WeatherAPI) -> None:
    weather_mock: dict[str, object] = {
        "lat": 33.7488,
        "lon": -84.3880,
        "timezone": "America/New_York",
        "timezone_offset": -14400,
        "current": {
            "dt": 1714728000,
            "sunrise": 1714702800,
            "sunset": 1714753200,
            "temp": 70.0,
            "feels_like": 68.0,
            "pressure": 1015,
            "humidity": 55,
            "wind_speed": 5,
            "wind_deg": 180,
            "uvi": 4.5,
            "weather": [
                {"id": 800, "main": "Clear", "description": "clear sky", "icon": "01d"}
            ],
        },
        "hourly": [],
        "daily": [],
    }

    aqi_mock: dict[str, object] = {
        "list": [{"main": {"aqi": 2}, "components": {"pm2_5": 12.0}}]
    }

    with patch("rpiweather.weather.api.requests.get") as mock_get:
        mock_weather_resp = Mock()
        mock_weather_resp.status_code = 200
        mock_weather_resp.text = json.dumps(weather_mock)
        mock_weather_resp.json.return_value = weather_mock

        mock_aqi_resp = Mock()
        mock_aqi_resp.status_code = 200
        mock_aqi_resp.json.return_value = aqi_mock

        mock_get.side_effect = [mock_weather_resp, mock_aqi_resp]

        result: WeatherResponse = api.fetch_weather()
        assert isinstance(result, WeatherResponse)
        assert result.current.temp == 70.0


def test_fetch_weather_bad_response(api: WeatherAPI) -> None:
    with patch("rpiweather.weather.api.requests.get") as mock_get:
        mock_resp = Mock()
        mock_resp.status_code = 401
        mock_resp.text = "Unauthorized"
        mock_resp.json.return_value = {"message": "Invalid API key"}
        mock_get.return_value = mock_resp

        with pytest.raises(WeatherAPIError) as excinfo:
            api.fetch_weather()

        assert "Invalid API key" in str(excinfo.value)
