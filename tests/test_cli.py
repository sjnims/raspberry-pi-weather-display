from typer.testing import CliRunner
from rpiweather.cli import app
from pathlib import Path

CONFIG_YAML = """\
api_key: "${OWM_API_KEY}"
lat: 42.774
lon: -78.787
city: Orchard Park
units: imperial
timezone: "America/New_York"
time_format_general: "%-I:%M %p"
time_format_hourly: "%-I %p"
time_format_daily: "%a"
time_format_full_date: "%A, %B %-d"
hourly_count: 8
daily_count: 5
refresh_minutes: 120
display_width: 800
display_height: 600
vcom_volts: -1.45
"""

runner = CliRunner()


def test_weather_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Usage" in result.output


def test_weather_config_validate() -> None:
    config_path = Path("config-sample.yaml")
    assert config_path.exists()
    result = runner.invoke(app, ["config", "validate", str(config_path)])
    assert result.exit_code == 0
    assert "Config valid" in result.output


def test_weather_preview_command(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(CONFIG_YAML)

    result = runner.invoke(
        app,
        ["run", "--preview", "--config", str(config_path), "--once"],
        env={"OWM_API_KEY": "test-api-key-123"},
    )
    print(result.output)
    assert result.exit_code == 0
