"""E-Ink Weather Display CLI application.

This module provides the command-line interface for the Raspberry Pi
Weather Display, including dashboard rendering, weather fetching,
power management, and configuration utilities.
"""

from __future__ import annotations

import logging
import subprocess
import sys
import tempfile
import webbrowser
from pathlib import Path
from typing import Any, cast
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

import typer
import yaml
from pydantic import ValidationError

from rpiweather.display.epaper import IT8951Display
from rpiweather.display.error_ui import ErrorRenderer
from rpiweather.display.protocols import DisplayDriver, MockDisplay
from rpiweather.display.render import (
    DashboardContextBuilder,
    TemplateRenderer,
    WkhtmlToPngRenderer,
)
from rpiweather.scheduler import Scheduler
from rpiweather.settings import ApplicationSettings, RefreshMode, UserSettings
from rpiweather.system.status import SystemStatus
from rpiweather.types.pijuice import PiJuiceLike
from rpiweather.utils import TimeUtils
from rpiweather.weather import (
    BatteryUtils,
    WeatherAPI,
    WeatherAPIError,
    WeatherIcons,
    WeatherResponse,
)

# ── CLI setup ────────────────────────────────────────────────────────────────
app = typer.Typer(help="E-Ink Weather Display CLI", add_completion=False)
config_app = typer.Typer(help="Config helpers")
app.add_typer(config_app, name="config")

logger: logging.Logger = logging.getLogger("rpiweather")

# Test configuration for creating test instances
TEST_CONFIG_YAML = """\
api_key: "test_api_key"
lat: 42.774
lon: -78.787
city: Test City
units: imperial
timezone: "America/New_York"
time_format_general: "%-I:%M %p"
time_format_hourly: "%-I %p"
time_format_daily: "%a"
time_format_full_date: "%A, %B %-d"
hourly_count: 8
daily_count: 5
refresh_minutes: 120
vcom_volts: -1.45
"""

# Options for the main command
CONFIG_OPTION = typer.Option(..., "--config", "-c", exists=True, dir_okay=False)
DEBUG_OPTION = typer.Option(False, "--debug", help="Enable debug logging")
DST_ARGUMENT = typer.Argument(..., help="Output config.yaml")
PREVIEW_OPTION = typer.Option(False, "--preview", "-p", help="Generate preview only")
ONCE_OPTION = typer.Option(False, "--once", "-1", help="Run one cycle then exit")
SERVE_OPTION = typer.Option(
    False, "--serve", "-s", help="Start a simple HTTP server to serve the preview directory"
)
STAY_AWAKE_URL_OPTION = typer.Option(None, help="Override URL that returns {'awake': true|false}")


class WeatherDisplay:
    """Main controller class for the weather display application.

    This class orchestrates the entire weather display workflow:
    - Loading configuration and initializing components
    - Fetching and processing weather data
    - Managing the battery and power state
    - Rendering the dashboard or error screens
    - Updating the e-ink display
    - Handling refresh cycles

    All application dependencies are initialized here, making this
    the central coordination point for the application.
    """

    pijuice: PiJuiceLike | None

    def __init__(
        self,
        config_path: Path,
        display_driver: DisplayDriver | None = None,
        weather_api: WeatherAPI | None = None,
        pijuice: PiJuiceLike | None = None,
        template_renderer: TemplateRenderer | None = None,
        context_builder: DashboardContextBuilder | None = None,
        png_renderer: WkhtmlToPngRenderer | None = None,
        debug: bool = False,
    ):
        """Initialize the weather display controller.

        Args:
            config_path: Path to config.yaml
            display_driver: Optional custom display driver
            weather_api: Optional custom weather API client
            pijuice: Optional PiJuice hardware interface
            template_renderer: Optional custom template renderer
            context_builder: Optional custom context builder
            png_renderer: Optional custom PNG renderer
            debug: Enable debug logging
        """
        # Configure logging
        logging.basicConfig(
            level=logging.DEBUG if debug else logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
        )

        # Load configuration and initialize services
        self.config: UserSettings = UserSettings.load(config_path)

        # Create centralized settings
        self.settings = ApplicationSettings(self.config)

        # Allow dependency injection or create defaults
        self.weather_api = weather_api or WeatherAPI(self.config)
        self.pijuice = pijuice or self._initialize_pijuice()
        self.error_streak = 0
        self.last_full_refresh = TimeUtils.now_localized()

        # Initialize renderers - allow dependency injection
        self.template_renderer = template_renderer or TemplateRenderer()
        self.context_builder = context_builder or DashboardContextBuilder(self.config)
        self.png_renderer = png_renderer or WkhtmlToPngRenderer()

        # Dependency-injected display driver
        self.display_driver = display_driver or IT8951Display()

        # Load weather icon mapping
        WeatherIcons.load_mapping()

    def _initialize_pijuice(self) -> PiJuiceLike | None:
        """Initialize PiJuice hardware interface if available."""
        try:
            # Attempt to import PiJuice library
            import pijuice  # type: ignore

            pj: PiJuiceLike = pijuice.PiJuice(1, 0x14)  # type: ignore[assignment]

            self._ensure_rtc_synced(pj)  # type: ignore[no-untyped-call]
            return pj  # type: ignore[return-value]
        except Exception as exc:
            logger.debug("PiJuice not available: %s", exc)
            return None

    def _ensure_rtc_synced(self, pijuice: PiJuiceLike) -> None:
        """Ensure the PiJuice RTC is synchronized with system time."""
        try:
            rtc_time = pijuice.RTC.GetTime()["data"]
            if rtc_time["year"] < 2024:
                pijuice.RTC.SetTime()
                logger.info("RTC set from system clock")
        except Exception as exc:
            logger.debug("RTC sync skipped: %s", exc)

    def get_battery_status(self) -> tuple[int, bool, bool]:
        """Get current battery status information.

        Returns:
            Tuple of (state_of_charge, is_charging, battery_warning)
        """
        soc = 100
        is_charging = False
        battery_warning = False

        if self.pijuice:
            try:
                soc = self.pijuice.status.GetChargeLevel()["data"]
                batt = BatteryUtils.get_battery_status(self.pijuice)
                is_charging = batt["is_charging"]
                battery_warning = batt.get("battery_warning", False)
            except Exception as exc:
                logger.warning("Could not get battery status: %s", exc)

        return soc, is_charging, battery_warning

    def _get_system_status(self) -> SystemStatus:
        """Get current system status including battery information.

        Returns:
            SystemStatus object with battery and system information
        """
        soc, is_charging, battery_warning = self.get_battery_status()
        return SystemStatus(
            soc=soc,
            is_charging=is_charging,
            battery_warning=battery_warning,
        )

    def _fetch_weather_data(self) -> WeatherResponse:
        """Fetch the current weather data."""
        weather = self.weather_api.fetch_weather()
        self._prepare_localized_timestamps(weather)
        return weather

    def fetch_and_render(
        self,
        preview: bool = False,
        mode: RefreshMode = RefreshMode.GREYSCALE,
        serve: bool = False,
        once: bool = False,
    ) -> bool:
        """Fetch weather data and render the dashboard.

        This is the main application workflow, orchestrating:
        1. Retrieving battery status
        2. Fetching weather data from OpenWeather API
        3. Preparing timestamps for display
        4. Rendering the dashboard or error screen
        5. Optionally serving a preview in a browser
        6. Updating the e-ink display

        Args:
            preview: Generate preview HTML only (no PNG or display)
            mode: RefreshMode to use for display update
            serve: Start a local HTTP server to view preview
            once: Run one cycle then exit

        Returns:
            True if successful, False on error
        """
        # Get system status
        status = self._get_system_status()

        # Fetch weather data
        try:
            weather = self._fetch_weather_data()
        except WeatherAPIError as err:
            logger.error("OpenWeather error (%s): %s", err.code, err.message)
            if not preview:
                self._render_error_screen(err, status.soc, status.is_charging)
            return False

        # Render dashboard
        return self.render_dashboard(
            weather,
            preview,
            mode,
            status,
            serve,
            once,
        )

    def _prepare_localized_timestamps(self, weather: WeatherResponse) -> None:
        """Prepare localized timestamps for display.

        Args:
            weather: Weather response object
        """
        local_tz = ZoneInfo(self.config.timezone)
        time_fmt = self.config.time_format_general

        # Add localized sunrise/sunset times to daily forecasts
        for d in weather.daily:
            d.sunrise_local = d.sunrise.astimezone(local_tz).strftime(time_fmt)
            d.sunset_local = d.sunset.astimezone(local_tz).strftime(time_fmt)

        # Add localized sunrise/sunset times to current forecast
        weather.current.sunrise_local = weather.current.sunrise.astimezone(local_tz).strftime(
            time_fmt
        )
        weather.current.sunset_local = weather.current.sunset.astimezone(local_tz).strftime(
            time_fmt
        )

    def render_dashboard(
        self,
        weather: WeatherResponse,
        preview: bool = PREVIEW_OPTION,
        mode: RefreshMode = RefreshMode.GREYSCALE,
        status: SystemStatus | None = None,
        serve: bool = SERVE_OPTION,
        once: bool = ONCE_OPTION,
    ) -> bool:
        """Render the dashboard HTML/PNG and update display."""
        # Ensure we have a valid SystemStatus object
        system_status = status or SystemStatus(
            soc=100,  # Default to 100% if no battery info
            is_charging=False,
            battery_warning=False,
        )

        # Build template context using OO approach
        ctx: dict[str, Any] = self.context_builder.build_dashboard_context(weather, system_status)

        # Render HTML template using OO approach
        html = self.template_renderer.dashboard_template.render(**ctx)
        out_dir = self.settings.paths.preview_dir
        out_dir.mkdir(parents=True, exist_ok=True)

        html_path = out_dir / self.settings.paths.preview_html
        png_path = out_dir / self.settings.paths.preview_png
        html_path.write_text(html, encoding="utf-8")

        # Generate PNG for display using OO approach
        if not preview:
            self.png_renderer.render_to_image(html, png_path)

        # Serve preview in browser if requested
        if serve and preview and once:
            self._serve_preview_in_browser()

        # Update e-ink display
        if not preview:
            self.display_driver.display_image(png_path, mode=mode)

        return True

    def _serve_preview_in_browser(self) -> None:
        """Start HTTP server and open browser for preview."""
        url = f"http://localhost:8000/{self.settings.paths.preview_html}"
        typer.echo(f"Serving preview on {url} - press Ctrl-C to quit")

        try:
            webbrowser.open_new_tab(url)
        except Exception as exc:
            logger.debug("Could not open browser: %s", exc)

        subprocess.call(
            [
                "python3",
                "-m",
                "http.server",
                "8000",
                "--directory",
                self.settings.paths.preview_dir,
            ]
        )

    def _render_error_screen(self, error: WeatherAPIError, soc: int, is_charging: bool) -> None:
        """Render error screen on display.

        Args:
            error: Weather API error
            soc: Battery state of charge
            is_charging: Whether battery is charging
        """
        with tempfile.TemporaryDirectory() as td:
            error_png = Path(td) / "error.png"

            # Render and display the error screen using ErrorRenderer
            renderer = ErrorRenderer(
                html_renderer=self.png_renderer,
                display_driver=self.display_driver,
            )
            renderer.render_error(
                error_message=f"API Error ({error.code}): {error.message}",
                system_status=SystemStatus(soc, is_charging),
                output_path=error_png,
                display_immediately=True,
            )

    @classmethod
    def create_for_testing(
        cls,
        config_path: Path | None = None,
        mock_weather_data: dict[str, Any] | None = None,
        mock_battery_status: tuple[int, bool, bool] = (100, False, False),
        mock_display_driver: DisplayDriver | None = None,
    ) -> WeatherDisplay:
        """Create WeatherDisplay instance configured for testing.

        Args:
            config_path: Path to config file (creates default if None)
            mock_weather_data: Mock weather data to return
            mock_battery_status: Mock battery status as (soc, is_charging, warning)
            mock_display_driver: Mock display driver

        Returns:
            WeatherDisplay instance configured for testing
        """

        if config_path is None:
            # Create temp config file with reasonable defaults
            with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as temp:
                temp_path = Path(temp.name)
                temp_path.write_text(TEST_CONFIG_YAML)
                config_path = temp_path

        # Create mock weather API if requested
        mock_api = None
        if mock_weather_data:
            mock_api = MagicMock(spec=WeatherAPI)
            mock_api.fetch_weather.return_value = WeatherResponse(**mock_weather_data)

        # Create mock PiJuice if requested
        mock_pijuice = None
        if mock_battery_status != (100, False, False):
            mock_pijuice = MagicMock(spec=PiJuiceLike)
            # Configure the mock to return the requested battery status
            soc, is_charging, battery_warning = mock_battery_status

            # Mock the status.GetChargeLevel() method
            mock_status = MagicMock()
            mock_status.GetChargeLevel.return_value = {"data": soc}
            mock_pijuice.status = mock_status

            # Configure BatteryUtils.get_battery_status to return the right values
            # Note: This is a bit of a hack, normally we'd use monkeypatch in tests
            BatteryUtils.get_battery_status = MagicMock(
                return_value={
                    "is_charging": is_charging,
                    "battery_warning": battery_warning,
                }
            )

        return cls(
            config_path=config_path,
            display_driver=mock_display_driver or MockDisplay(),
            weather_api=mock_api,
            pijuice=mock_pijuice,
            debug=True,
        )


# ───────────────────────── main command ─────────────────────────────────────


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
