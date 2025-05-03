from typer.testing import CliRunner
from rpiweather.cli import app
from pathlib import Path

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
