"""Dashboard rendering components for weather display."""

from __future__ import annotations

import platform
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional, cast

from jinja2 import Environment, FileSystemLoader, Template, select_autoescape

from rpiweather.settings import UserSettings, ApplicationSettings
from rpiweather.display.protocols import HtmlRenderer
from rpiweather.system.status import SystemStatus
from rpiweather.weather.api import WeatherResponse
from rpiweather.weather.utils import (
    WeatherIcons,
    UnitConverter,
    PrecipitationUtils,
)
from rpiweather.utils import TimeUtils


# Top-level exports for Pyright
def wind_rotation(deg: float | None, direction: str = "towards") -> str | None:
    """Return CSS rotation for wind bearing, or None if input is None."""
    return f"rotate({(deg + 180) % 360}deg)" if deg is not None else None


ts_to_dt = TimeUtils.to_local_datetime


# Define classes first
class TemplateRenderer:
    """Handles Jinja2 template environment and rendering.

    This class configures a Jinja2 environment with custom filters
    for the weather dashboard. It provides methods to render templates
    with weather and system data.

    Capabilities:
    - Custom template filters for weather data formatting
    - Helper functions for date/time formatting
    - Wind direction and icon conversion
    - Static asset resolution

    The renderer uses paths from application settings by default,
    but can be configured with custom template directories.
    """

    dashboard_template: Template

    def __init__(
        self,
        templates_dir: Optional[Path] = None,
        user_settings: Optional[UserSettings] = None,
    ) -> None:
        """Initialize the template renderer.

        Args:
            templates_dir: Directory containing templates (default: from settings)
            user_settings: User configuration
        """
        self.user_settings = user_settings or UserSettings.load()
        self.app_settings = ApplicationSettings(self.user_settings)

        if templates_dir:
            self.templates_dir = templates_dir
        else:
            self.templates_dir = self.app_settings.paths.templates_dir
            self.static_dir = self.app_settings.paths.static_dir

        # Create Jinja environment with custom filters
        self.env = Environment(
            loader=FileSystemLoader(self.templates_dir),
            autoescape=select_autoescape(["html"]),
        )

        def _url_for(endpoint: str, filename: str = "") -> str:
            """Simple url_for implementation for static assets."""
            if endpoint == "static":
                return f"static/{filename}"
            raise ValueError(f"Unsupported endpoint: {endpoint}")

        # Expose under common names in templates
        self.env.globals.update(
            {
                "url_for": _url_for,
            }
        )

        # Register filters
        self._register_filters()

        self.dashboard_template = self.env.get_template("dashboard.html.j2")

    def _register_filters(self) -> None:
        """Register custom filters with the Jinja environment."""
        self.env.filters.update(
            {
                "deg_to_cardinal": UnitConverter.deg_to_cardinal,
                "weather_icon": WeatherIcons.get_icon_filename,
                "moon_phase_icon": WeatherIcons.get_moon_phase_icon,
                "moon_phase_label": WeatherIcons.get_moon_phase_label,
                "wind_rotation": wind_rotation,
                "ts_to_dt": ts_to_dt,
                "strftime": TimeUtils.format_datetime,
            }
        )

    def render_dashboard(self, **context: Any) -> str:
        """Render the dashboard template with the provided context.

        Args:
            context: Template context variables

        Returns:
            Rendered HTML
        """
        return cast(str, self.dashboard_template.render(**context))  # type: ignore


class DashboardContextBuilder:
    """Builds context data for dashboard templates.

    Transforms raw weather and system data into a complete template context
    with derived values, formatting preferences, and unit conversions ready
    for rendering.

    The builder:
    - Processes hourly and daily forecast data
    - Applies the user's unit preferences (metric/imperial)
    - Formats dates and times according to user settings
    - Calculates additional values like UVI max, daylight hours, etc.
    - Prepares icon and label mappings
    """

    def __init__(self, user_settings: Optional[UserSettings] = None) -> None:
        """Initialize with configuration.

        Args:
            user_settings: User configuration
        """
        self.user_settings = user_settings or UserSettings.load()
        self.app_settings = ApplicationSettings(self.user_settings)

    def build_dashboard_context(
        self,
        weather: WeatherResponse,
        system_status: SystemStatus,
    ) -> Dict[str, Any]:
        """Build complete context for dashboard template.

        Args:
            weather: Weather response data
            system_status: System status information

        Returns:
            Template context dictionary
        """
        now = TimeUtils.now_localized()
        today_local = now.date()

        # Extract UV index data
        uvi_slice = [
            (h.dt, h.uvi)
            for h in weather.hourly
            if h.dt.astimezone().date() == today_local and h.uvi is not None
        ]

        max_uvi_time = None
        max_uvi_time_str = None

        if uvi_slice:
            max_uvi_entry = max(uvi_slice, key=lambda x: x[1])
            max_uvi_time = max_uvi_entry[0].astimezone()
            max_uvi_time_str = TimeUtils.format_datetime(
                max_uvi_time, self.app_settings.formats.general
            )

        # Sun and moon information
        sunrise_dt = weather.current.sunrise
        sunset_dt = weather.current.sunset
        sunrise_str = TimeUtils.format_datetime(
            sunrise_dt, self.app_settings.formats.general
        )
        sunset_str = TimeUtils.format_datetime(
            sunset_dt, self.app_settings.formats.general
        )
        moon_phase = weather.daily[0].moon_phase if weather.daily else 0.0

        # Process hourly forecast
        hourly = [h for h in weather.hourly if h.dt.astimezone() > now][
            : self.user_settings.hourly_count
        ]
        for h in hourly:
            h.local_time = h.dt.astimezone().strftime(self.app_settings.formats.hourly)

        # Process daily forecast
        daily = [d for d in weather.daily if d.dt.astimezone().date() > today_local][
            : self.user_settings.daily_count
        ]
        for d in daily:
            d.weekday_short = d.dt.astimezone().strftime(
                self.app_settings.formats.daily
            )

        # Pressure conversion: OpenWeather returns pressure in hPa
        pressure_hpa = weather.current.pressure
        pressure_value = (
            pressure_hpa
            if self.user_settings.is_metric
            else UnitConverter.hpa_to_inhg(pressure_hpa)
        )

        # Build the complete context
        ctx = {
            "now": now,
            "date": TimeUtils.format_datetime(now, self.app_settings.formats.full_date),
            "last_refresh": now.strftime(self.app_settings.formats.general + " %Z"),
            "battery_soc": system_status.soc,
            "battery_warning": system_status.battery_warning,
            "is_charging": system_status.is_charging,
            "units_temp": "°C" if self.user_settings.is_metric else "°F",
            "units_wind": "m/s" if self.user_settings.is_metric else "mph",
            "units_pressure": "hPa" if self.user_settings.is_metric else "inHg",
            "pressure": pressure_value,
            "hourly": hourly,
            "daily": daily,
            "sunrise": sunrise_str,
            "sunset": sunset_str,
            "moon_phase": moon_phase,
            "moon_phase_icon": WeatherIcons.get_moon_phase_icon,
            "moon_phase_label": WeatherIcons.get_moon_phase_label,
            "uvi_time": max_uvi_time_str,
            "current": weather.current,
            "hourly_precip": PrecipitationUtils.hourly_precip,
            "city": self.user_settings.city,
            "daylight": TimeUtils.get_time_difference_string(sunrise_dt, sunset_dt),
            "uvi_max": max((uvi[1] for uvi in uvi_slice), default=0),
            "uvi_occurred": max_uvi_time is not None and now > max_uvi_time,
            "bft": UnitConverter.beaufort_from_speed(weather.current.wind_speed),
            "aqi": weather.air_quality.aqi if weather.air_quality else "N/A",
        }

        return ctx


class WkhtmlToPngRenderer(HtmlRenderer):
    """HTML to PNG renderer using wkhtmltoimage.

    Converts HTML content to PNG images using the wkhtmltoimage command-line
    tool, which must be installed on the system. On Linux, it uses xvfb-run
    to handle headless rendering.

    This renderer supports custom dimensions (width/height) for the output
    image, with defaults from user settings for the e-ink display.

    Note: Requires wkhtmltopdf (https://wkhtmltopdf.org/) installed on the
    system, and on Linux also requires xvfb.
    """

    def __init__(
        self,
        width: Optional[int] = None,
        height: Optional[int] = None,
        user_settings: Optional[UserSettings] = None,
    ) -> None:
        """Initialize renderer with optional custom dimensions.

        Args:
            width: Custom width in pixels (default: from user settings)
            height: Custom height in pixels (default: from user settings)
            user_settings: User configuration (default: loaded from config.yaml)
        """
        self.user_settings = user_settings or UserSettings.load()
        self.width = width or self.user_settings.display_width
        self.height = height or self.user_settings.display_height

    def render_to_image(self, html: str, output_path: Path) -> None:
        """Render HTML to PNG.

        Args:
            html: HTML content to render
            output_path: Path where the image will be saved
        """
        html_path = output_path.with_suffix(".html")
        html_path.write_text(html, "utf-8")

        cmd = [
            "wkhtmltoimage",
            "--width",
            str(self.width),
            "--height",
            str(self.height),
            html_path.as_posix(),
            output_path.as_posix(),
        ]

        if platform.system() == "Linux":
            cmd = ["xvfb-run", "-a"] + cmd

        subprocess.run(cmd, check=True)


__all__ = ["ts_to_dt", "wind_rotation"]
