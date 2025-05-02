"""E-Ink Weather Display CLI application.

This module provides the command-line interface for the Raspberry Pi
Weather Display, including dashboard rendering, weather fetching,
power management, and configuration utilities.
"""

from __future__ import annotations

# ── standard library ─────────────────────────────────────────────────────────
import logging
import subprocess
import sys
import tempfile
import webbrowser
from pathlib import Path
from typing import Any, Dict, Optional
from zoneinfo import ZoneInfo

# ── third‑party ──────────────────────────────────────────────────────────────
import typer
import yaml
from pydantic import ValidationError

# ── rpiweather packages ──────────────────────────────────────────────────────
from rpiweather.config import WeatherConfig
from rpiweather.display.epaper import IT8951Display
from rpiweather.display.protocols import DisplayDriver
from rpiweather.display.error_ui import ErrorRenderer
from rpiweather.constants import (
    PREVIEW_DIR,
    PREVIEW_HTML_NAME,
    PREVIEW_PNG_NAME,
    RefreshMode,
)
from rpiweather.display.render import (
    DashboardContextBuilder,
    TemplateRenderer,
    WkhtmlToPngRenderer,
)
from rpiweather.system.status import SystemStatus
from rpiweather.types.pijuice import PiJuiceLike
from rpiweather.utils import TimeUtils
from rpiweather.weather import (
    WeatherAPI,
    WeatherAPIError,
    WeatherIcons,
    WeatherResponse,
    BatteryUtils,
)
from rpiweather.scheduler import Scheduler

# ── CLI setup ────────────────────────────────────────────────────────────────
app = typer.Typer(help="E-Ink Weather Display CLI", add_completion=False)
config_app = typer.Typer(help="Config helpers")
app.add_typer(config_app, name="config")

logger: logging.Logger = logging.getLogger("rpiweather")

DEFAULT_STAY_AWAKE_URL = "http://localhost:8000/stay_awake.json"
MIN_SHUTDOWN_SLEEP_MIN = 20  # don't power‑off for very short sleeps


class WeatherDisplay:
    """Main controller class for the weather display application."""

    pijuice: Optional[PiJuiceLike]  # Add this explicit field type

    def __init__(
        self,
        config_path: Path,
        display_driver: DisplayDriver | None = None,
        debug: bool = False,
    ):
        """Initialize the weather display controller.

        Args:
            config_path: Path to config.yaml
            debug: Enable debug logging
        """
        # Configure logging
        logging.basicConfig(
            level=logging.DEBUG if debug else logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
        )

        # Load configuration and initialize services
        self.config: WeatherConfig = WeatherConfig.load(config_path)
        self.weather_api = WeatherAPI(self.config)
        self.pijuice = self._initialize_pijuice()
        self.error_streak = 0
        self.last_full_refresh = TimeUtils.now_localized()

        # Initialize renderers
        self.template_renderer = TemplateRenderer()
        self.context_builder = DashboardContextBuilder(self.config)
        self.png_renderer = WkhtmlToPngRenderer()

        # Dependency-injected display driver
        self.display_driver = display_driver or IT8951Display()

        # Load weather icon mapping
        WeatherIcons.load_mapping()

    def _initialize_pijuice(self) -> Optional["PiJuiceLike"]:
        """Initialize PiJuice hardware interface if available."""
        try:
            import pijuice  # type: ignore[import-not-found]

            # Add a cast to help the type checker
            from typing import cast

            pj = cast(PiJuiceLike, pijuice.PiJuice(1, 0x14))  # type: ignore[call-arg]

            self._ensure_rtc_synced(pj)
            return pj
        except Exception as exc:
            logger.debug("PiJuice not available: %s", exc)
            return None

    def _ensure_rtc_synced(self, pijuice: PiJuiceLike) -> None:
        """Ensure the PiJuice RTC is synchronized with system time.

        Args:
            pijuice: PiJuice hardware interface
        """
        try:
            rtc_time = pijuice.rtc.GetTime()["data"]  # type: ignore[attr-defined]
            if rtc_time["year"] < 2024:
                pijuice.rtc.SetTime()  # type: ignore[attr-defined]
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
                soc = self.pijuice.status.GetChargeLevel()["data"]  # type: ignore
                batt = BatteryUtils.get_battery_status(self.pijuice)
                is_charging = batt["is_charging"]
                battery_warning = batt.get("battery_warning", False)
            except Exception as exc:
                logger.warning("Could not get battery status: %s", exc)

        return soc, is_charging, battery_warning

    def fetch_and_render(
        self,
        preview: bool = False,
        mode: RefreshMode = RefreshMode.GREYSCALE,
        serve: bool = False,
        once: bool = False,
    ) -> bool:
        """Fetch weather data and render the dashboard.

        Args:
            preview: Generate preview HTML only (no PNG or display)
            mode: RefreshMode to use for display update
            serve: Start a local HTTP server to view preview
            once: Run one cycle then exit

        Returns:
            True if successful, False on error
        """
        soc, is_charging, battery_warning = self.get_battery_status()

        try:
            weather = self.weather_api.fetch_weather()
            self._prepare_localized_timestamps(weather)
            return self._render_dashboard(
                weather,
                preview,
                mode,
                soc,
                is_charging,
                battery_warning,
                serve,
                once,
            )
        except WeatherAPIError as err:
            logger.error("OpenWeather error (%s): %s", err.code, err.message)
            if not preview:
                self._render_error_screen(err, soc, is_charging)
            return False

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
        weather.current.sunrise_local = weather.current.sunrise.astimezone(
            local_tz
        ).strftime(time_fmt)
        weather.current.sunset_local = weather.current.sunset.astimezone(
            local_tz
        ).strftime(time_fmt)

    def _render_dashboard(
        self,
        weather: WeatherResponse,
        preview: bool,
        mode: RefreshMode,
        soc: int,
        is_charging: bool,
        battery_warning: bool,
        serve: bool,
        once: bool,
    ) -> bool:
        """Render the dashboard HTML/PNG and update display.

        Args:
            weather: Weather data to display
            preview: Generate preview HTML only
            mode: RefreshMode
                Which refresh mode to use (FULL or GREYSCALE).
            soc: Battery state of charge
            is_charging: Whether battery is charging
            battery_warning: Whether to show battery warning
            serve: Serve preview on HTTP server
            once: Exit after one cycle

        Returns:
            True if rendering was successful
        """

        # Build template context using OO approach
        status = SystemStatus(
            soc=soc,
            is_charging=is_charging,
            battery_warning=battery_warning,
        )
        ctx = self.context_builder.build_dashboard_context(weather, status)

        # Render HTML template using OO approach
        html = self.template_renderer.dashboard_template.render(**ctx)  # type: ignore[reportUnknownMemberType]
        out_dir = Path(PREVIEW_DIR)
        out_dir.mkdir(parents=True, exist_ok=True)

        html_path = out_dir / PREVIEW_HTML_NAME
        png_path = out_dir / PREVIEW_PNG_NAME
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
        url = f"http://localhost:8000/{PREVIEW_HTML_NAME}"
        typer.echo(f"Serving preview on {url} - press Ctrl-C to quit")

        try:
            webbrowser.open_new_tab(url)
        except Exception as exc:  # pragma: no cover
            logger.debug("Could not open browser: %s", exc)

        subprocess.call(
            ["python3", "-m", "http.server", "8000", "--directory", PREVIEW_DIR]
        )

    def _render_error_screen(
        self, error: WeatherAPIError, soc: int, is_charging: bool
    ) -> None:
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


# ───────────────────────── main command ─────────────────────────────────────
@app.command()
def run(
    config: Path = typer.Option(..., "--config", "-c", exists=True, dir_okay=False),
    preview: bool = typer.Option(False, "--preview", "-p"),
    serve: bool = typer.Option(
        False,
        "--serve",
        "-s",
        help="When used with --preview, start a simple HTTP server to serve the "
        "preview directory (use Ctrl-C to stop).",
    ),
    once: bool = typer.Option(False, "--once", "-1", help="Run one cycle then exit"),
    debug: bool = typer.Option(False, "--debug"),
    stay_awake_url: Optional[str] = typer.Option(
        None,
        help="Override URL that returns {'awake': true|false}. "
        "If omitted, value from config.yaml or the default URL is used.",
    ),
) -> None:
    """Run the weather display application."""
    display = WeatherDisplay(config, display_driver=IT8951Display(), debug=debug)
    scheduler = Scheduler(display, stay_awake_url)
    scheduler.run(preview, serve, once)


# ───────────────────────── config sub‑commands ───────────────────────────────
@config_app.command("validate")
def validate_config(file: Path):
    """Validate a YAML config file against the schema."""
    try:
        WeatherConfig.load(file)
        typer.echo("✅ Config valid")
    except RuntimeError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc


@config_app.command("wizard")
def wizard(dst: Path = typer.Argument(..., help="Output config.yaml")):
    """Interactive prompt to create a config file."""
    typer.echo("Interactive config builder - press Enter for defaults.")

    while True:
        data: Dict[str, Any] = {
            "lat": float(typer.prompt("Latitude")),
            "lon": float(typer.prompt("Longitude")),
            "city": typer.prompt("City name"),
            "api_key": typer.prompt("OpenWeather API key", hide_input=True),
            "units": typer.prompt("Units [imperial|metric]", default="imperial"),
        }
        try:
            cfg = WeatherConfig(**data)
            break  # valid → exit loop
        except ValidationError as err:
            typer.secho("\nConfig error(s):", fg=typer.colors.RED, err=True)
            for e in err.errors():
                typer.secho(
                    f"  • {e['loc'][0]} - {e['msg']}", fg=typer.colors.RED, err=True
                )
            typer.echo("Please re-enter the values.\n")

    dst.write_text(yaml.safe_dump(cfg.model_dump(), sort_keys=False), encoding="utf-8")
    typer.secho(f"Config written to {dst}", fg=typer.colors.GREEN)


# ───────────────────────── module entrypoint ────────────────────────────────
if __name__ == "__main__":
    try:
        app()
    except KeyboardInterrupt:
        sys.exit(0)
