"""E-Ink Weather Display CLI application.

This module provides the command-line interface for the Raspberry Pi
Weather Display, including dashboard rendering, weather fetching,
power management, and configuration utilities.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any, Final, cast

import typer
import yaml
from pydantic import ValidationError

from rpiweather.controller import WeatherDisplay
from rpiweather.display.epaper import IT8951Display
from rpiweather.display.protocols import DisplayDriver, MockDisplay
from rpiweather.scheduling import Scheduler
from rpiweather.settings.application import UserSettings
from rpiweather.types.pijuice import PiJuiceLike
from rpiweather.weather.api import WeatherAPI

# ── CLI setup ────────────────────────────────────────────────────────────────
app = typer.Typer(help="E-Ink Weather Display CLI", add_completion=False)
config_app = typer.Typer(help="Config helpers")
app.add_typer(config_app, name="config")

logger: Final = logging.getLogger(__name__)  # Will be "rpiweather.cli"

# Options for the main command
CONFIG_OPTION = typer.Option(..., "--config", "-c", exists=True, dir_okay=False)
DEBUG_OPTION = typer.Option(False, "--debug", help="Enable debug logging")
DST_ARGUMENT = typer.Argument(..., help="Output config.yaml")
STAY_AWAKE_URL_OPTION = typer.Option(None, help="Override URL that returns {'awake': true|false}")
PREVIEW_OPTION = typer.Option(False, "--preview", "-p", help="Generate preview only")
ONCE_OPTION = typer.Option(False, "--once", "-1", help="Run one cycle then exit")
SERVE_OPTION = typer.Option(
    False, "--serve", "-s", help="Start a simple HTTP server to serve the preview directory"
)


@app.command()
def run(
    config: Path = CONFIG_OPTION,
    preview: bool = PREVIEW_OPTION,
    serve: bool = SERVE_OPTION,
    once: bool = ONCE_OPTION,
    debug: bool = DEBUG_OPTION,
    stay_awake_url: str | None = STAY_AWAKE_URL_OPTION,
    # For testing only - HIDDEN from CLI but typed for pyright
    display_driver: str | None = typer.Option(None, hidden=True),
    weather_api: str | None = typer.Option(None, hidden=True),
    pijuice: str | None = typer.Option(None, hidden=True),
) -> None:
    """Run the weather display application."""
    display = WeatherDisplay(
        config,
        display_driver=cast(DisplayDriver | None, display_driver) or IT8951Display(),
        weather_api=cast(WeatherAPI | None, weather_api),
        pijuice=cast(PiJuiceLike | None, pijuice),
        debug=debug,
    )

    scheduler = Scheduler(display, stay_awake_url or display.settings.stay_awake_url.url)
    scheduler.run(preview, serve, once)


@app.command()
def preview(
    config: Path = CONFIG_OPTION,
    debug: bool = DEBUG_OPTION,
    # Testing options
    display_driver: str | None = typer.Option(None, hidden=True),
    weather_api: str | None = typer.Option(None, hidden=True),
    pijuice: str | None = typer.Option(None, hidden=True),
) -> None:
    """Start a preview server for the weather display.

    This renders the dashboard in a web browser and starts a local server.
    Press Ctrl+C to exit.
    """
    # Create the display controller
    display = WeatherDisplay(
        config,
        display_driver=cast(DisplayDriver | None, display_driver) or MockDisplay(),
        weather_api=cast(WeatherAPI | None, weather_api),
        pijuice=cast(PiJuiceLike | None, pijuice),
        debug=debug,
    )

    # Fetch and render in preview mode (generates the HTML/PNG files)
    if not display.fetch_and_render(preview=True, once=True):
        typer.echo("Failed to generate preview", err=True)
        raise typer.Exit(code=1)

    # Start the server
    url = display.serve_preview_in_browser()
    typer.echo(f"Serving preview on {url} - press Ctrl+C to quit")


# ───────────────────────── config sub-commands ───────────────────────────────
@config_app.command("validate")
def validate_config(file: Path):
    """Validate a YAML config file against the schema."""
    try:
        UserSettings.load(file)
        typer.echo("✅ Config valid")
    except RuntimeError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc


@config_app.command("wizard")
def wizard(dst: Path = DST_ARGUMENT):
    """Interactive prompt to create a config file."""
    typer.echo("Interactive config builder - press Enter for defaults.")

    while True:
        data: dict[str, Any] = {
            "lat": float(typer.prompt("Latitude")),
            "lon": float(typer.prompt("Longitude")),
            "city": typer.prompt("City name"),
            "api_key": typer.prompt("OpenWeather API key", hide_input=True),
            "units": typer.prompt("Units [imperial|metric]", default="imperial"),
        }
        try:
            cfg = UserSettings(**data)
            break  # valid → exit loop
        except ValidationError as err:
            typer.secho("\nConfig error(s):", fg=typer.colors.RED, err=True)
            for e in err.errors():
                typer.secho(f"  • {e['loc'][0]} - {e['msg']}", fg=typer.colors.RED, err=True)
            typer.echo("Please re-enter the values.\n")

    dst.write_text(yaml.safe_dump(cfg.model_dump(), sort_keys=False), encoding="utf-8")
    typer.secho(f"Config written to {dst}", fg=typer.colors.GREEN)


# ───────────────────────── module entrypoint ────────────────────────────────
if __name__ == "__main__":
    try:
        app()
    except KeyboardInterrupt:
        sys.exit(0)
