from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from rpiweather.display.render import (
    DashboardContextBuilder,
    TemplateRenderer,
    WkhtmlToPngRenderer,
    ts_to_dt,
    wind_rotation,
)
from rpiweather.settings.user import UserSettings
from rpiweather.system.status import SystemStatus
from rpiweather.weather.models import WeatherResponse


@pytest.fixture
def config() -> UserSettings:
    return UserSettings(
        api_key="test-key-123",
        lat=33.88,
        lon=-84.51,
        city="Testville",
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
        hourly_count=6,
        daily_count=5,
        quiet_hours=None,
    )


@pytest.fixture
def sample_status() -> SystemStatus:
    return SystemStatus(soc=90, is_charging=False)


@pytest.fixture
def sample_weather(weather_response: WeatherResponse) -> WeatherResponse:
    return weather_response


def test_context_builder_outputs_required_keys(
    sample_weather: WeatherResponse, sample_status: SystemStatus
) -> None:
    builder = DashboardContextBuilder()
    ctx = builder.build_dashboard_context(sample_weather, sample_status)
    assert "current" in ctx
    assert "uvi_max" in ctx
    assert "moon_phase_label" in ctx


def test_template_renderer_generates_html(
    sample_weather: WeatherResponse, sample_status: SystemStatus, config: UserSettings
) -> None:
    builder = DashboardContextBuilder()
    ctx = builder.build_dashboard_context(sample_weather, sample_status)
    renderer = TemplateRenderer()
    html = renderer.render_dashboard(**ctx)
    assert isinstance(html, str)
    assert "<html" in html.lower()
    assert ctx["city"] in html


def test_png_renderer_runs_subprocess(tmp_path: Path) -> None:
    renderer = WkhtmlToPngRenderer(width=800, height=600)
    html = "<html><body><h1>Hello</h1></body></html>"
    output_path = tmp_path / "test_output.png"

    with patch("subprocess.run") as mock_run:
        renderer.render_to_image(html, output_path)
        mock_run.assert_called()
        assert output_path.name in str(mock_run.call_args[0][0])


def test_ts_to_dt_converts_epoch_to_datetime() -> None:
    dt = ts_to_dt(1714785600)  # 2024-05-04T12:00:00Z
    assert isinstance(dt, datetime)
    assert dt.year == 2024
    assert dt.month == 5
    assert dt.day == 4
    assert dt.tzinfo is not None
    assert dt.tzinfo.utcoffset(dt) == timedelta(0)


def test_wind_rotation_returns_correct_css_angle() -> None:
    assert wind_rotation(0) == "rotate(180deg)"
    assert wind_rotation(90) == "rotate(270deg)"
    assert wind_rotation(180) == "rotate(0deg)"
    assert wind_rotation(270) == "rotate(90deg)"
    assert wind_rotation(None) is None
