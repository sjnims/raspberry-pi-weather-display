import pytest

from rpiweather.settings.user import UserSettings
from rpiweather.weather.api import WeatherAPI
from rpiweather.weather.models import WeatherResponse


@pytest.fixture
def config() -> UserSettings:
    return UserSettings(
        api_key="test-key12345",
        lat=40.7128,
        lon=-74.0060,
        city="New York",
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
        timezone="America/New_York",
        stay_awake_url=None,
        hourly_count=3,
        daily_count=2,
    )


@pytest.fixture
def sample_weather() -> WeatherResponse:
    return WeatherResponse.model_validate(
        {
            "lat": 40.7128,
            "lon": -74.0060,
            "timezone": "America/New_York",
            "timezone_offset": -14400,
            "current": {
                "dt": 1714728000,
                "sunrise": 1714702800,
                "sunset": 1714753200,
                "temp": 72.0,
                "feels_like": 70.0,
                "pressure": 1012,
                "humidity": 50,
                "wind_speed": 6.0,
                "wind_deg": 200,
                "uvi": 5.5,
                "weather": [
                    {
                        "id": 801,
                        "main": "Clouds",
                        "description": "few clouds",
                        "icon": "02d",
                    }
                ],
            },
            "hourly": [],
            "daily": [
                {
                    "dt": 1714761600,
                    "sunrise": 1714702800,
                    "sunset": 1714753200,
                    "moon_phase": 0.5,
                    "temp": {
                        "min": 65.0,
                        "max": 75.0,
                        "day": 70.0,
                        "night": 66.0,
                        "eve": 68.0,
                        "morn": 67.0,
                    },
                    "weather": [
                        {
                            "id": 500,
                            "main": "Rain",
                            "description": "light rain",
                            "icon": "10d",
                        }
                    ],
                }
            ],
        }
    )


def test_build_context_keys(
    config: UserSettings, sample_weather: WeatherResponse
) -> None:
    api = WeatherAPI(config)
    ctx = api.build_context(sample_weather)

    assert ctx["city"] == "New York"
    assert "date" in ctx
    assert "uvi_max" in ctx
    assert "sunrise" in ctx
    assert "daylight" in ctx
    assert "moon_phase" in ctx
    assert "arrow_deg" in ctx
    assert isinstance(ctx["moon_phase_label"](0.5), str)
    assert isinstance(ctx["weather_icon"]("01d"), str)
    assert callable(ctx["hourly_precip"])
    assert isinstance(ctx["hourly"], list)
    assert isinstance(ctx["daily"], list)


def test_context_sets_weekday_short(
    config: UserSettings, sample_weather: WeatherResponse
) -> None:
    ctx = WeatherAPI(config).build_context(sample_weather)
    for day in ctx["daily"]:
        assert isinstance(day.weekday_short, str)
        assert len(day.weekday_short) >= 2
