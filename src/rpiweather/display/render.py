"""Dashboard rendering components for weather display."""

from __future__ import annotations

import platform
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional, cast
from zoneinfo import ZoneInfo

from jinja2 import Environment, FileSystemLoader, Template, Undefined, select_autoescape

from rpiweather.config import WeatherConfig
from rpiweather.display.protocols import HtmlRenderer
from rpiweather.system.status import SystemStatus
from rpiweather.weather.api import WeatherResponse
from rpiweather.weather.helpers import (
    beaufort_from_speed,
    deg_to_cardinal,
    get_moon_phase_icon_filename,
    get_moon_phase_label,
    get_weather_icon_filename,
    hourly_precip,
)


# Define classes first
class TemplateRenderer:
    """Handles Jinja2 template environment and rendering."""

    dashboard_template: Template

    def __init__(self, templates_dir: Optional[Path] = None) -> None:
        """Initialize the template renderer.

        Args:
            templates_dir: Directory containing templates (default: project's templates/)
        """
        project_root = Path(__file__).resolve().parents[3]  # repo root
        self.templates_dir = templates_dir or project_root / "templates"
        self.static_dir = project_root / "static"

        # Create Jinja environment with custom filters
        self.env = Environment(
            loader=FileSystemLoader(self.templates_dir),
            autoescape=select_autoescape(["html"]),
        )

        # Register filters
        self._register_filters()

        self.dashboard_template = self.env.get_template("dashboard.html.j2")

    def _register_filters(self) -> None:
        """Register custom filters with the Jinja environment."""
        self.env.filters.update(
            {
                "deg_to_cardinal": deg_to_cardinal,
                "weather_icon": get_weather_icon_filename,
                "moon_phase_icon": get_moon_phase_icon_filename,
                "moon_phase_label": get_moon_phase_label,
                "wind_rotation": self._wind_rotation,
                "ts_to_dt": self._ts_to_local,
                "strftime": self._dt_format,
            }
        )

    @staticmethod
    def _wind_rotation(deg: float, direction: str = "towards") -> float:
        """Return adjusted wind bearing for 'from' or 'towards' arrow."""
        return deg if direction == "towards" else (deg + 180) % 360

    @staticmethod
    def _ts_to_local(ts: int, timezone: str = "UTC") -> datetime:
        """Convert POSIX timestamp to local datetime."""
        return datetime.fromtimestamp(ts, tz=ZoneInfo(timezone))

    @staticmethod
    def _dt_format(d: datetime, fmt: str = "%-I %p") -> str:
        """strftime wrapper usable as a Jinja filter."""
        if isinstance(fmt, Undefined):
            fmt = "%-I %p"
        return d.strftime(fmt)

    def render_dashboard(self, **context: Any) -> str:
        """Render the dashboard template with the provided context.

        Args:
            context: Template context variables

        Returns:
            Rendered HTML
        """
        return cast(str, self.dashboard_template.render(**context))  # type: ignore

    def get_template(self, template_name: str) -> Template:
        """Get a template by name.

        Args:
            template_name: Template filename

        Returns:
            Jinja2 Template object
        """
        return self.env.get_template(template_name)


class DashboardContextBuilder:
    """Builds context data for dashboard templates."""

    def __init__(self, config: WeatherConfig) -> None:
        """Initialize with configuration.

        Args:
            config: Weather display configuration
        """
        self.config = config

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
        now = datetime.now(ZoneInfo(self.config.timezone))
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
            max_uvi_time_str = max_uvi_time.strftime(self.config.time_format_general)

        # Sun and moon information
        sunrise_dt = weather.current.sunrise
        sunset_dt = weather.current.sunset
        sunrise_str = sunrise_dt.strftime(self.config.time_format_general)
        sunset_str = sunset_dt.strftime(self.config.time_format_general)
        moon_phase = weather.daily[0].moon_phase if weather.daily else 0.0

        # Process hourly forecast
        hourly = [h for h in weather.hourly if h.dt.astimezone() > now][
            : self.config.hourly_count
        ]
        for h in hourly:
            h.local_time = h.dt.astimezone().strftime(self.config.time_format_hourly)

        # Process daily forecast
        daily = [d for d in weather.daily if d.dt.astimezone().date() > today_local][
            : self.config.daily_count
        ]
        for d in daily:
            d.weekday_short = d.dt.astimezone().strftime("%a")

        # Build the complete context
        ctx = {
            "now": now,
            "date": now.strftime("%A, %B %-d"),
            "last_refresh": now.strftime(self.config.time_format_general + " %Z"),
            "soc": system_status.soc,
            "battery_soc": system_status.soc,
            "battery_warning": system_status.battery_warning,
            "is_charging": system_status.is_charging,
            "units_temp": "°C" if self.config.units == "metric" else "°F",
            "units_wind": "m/s" if self.config.units == "metric" else "mph",
            "units_pressure": "hPa" if self.config.units == "metric" else "inHg",
            "hourly": hourly,
            "daily": daily,
            "sunrise": sunrise_str,
            "sunset": sunset_str,
            "moon_phase": moon_phase,
            "moon_phase_icon": get_moon_phase_icon_filename,
            "moon_phase_label": get_moon_phase_label,
            "uvi_time": max_uvi_time_str,
            "current": weather.current,
            "hourly_precip": hourly_precip,
            "city": self.config.city,
            "daylight": f"{(sunset_dt - sunrise_dt).seconds // 3600}h {(sunset_dt - sunrise_dt).seconds % 60}m",
            "uvi_max": max((uvi[1] for uvi in uvi_slice), default=0),
            "uvi_occurred": max_uvi_time is not None and now > max_uvi_time,
            "bft": beaufort_from_speed(weather.current.wind_speed),
            "aqi": weather.air_quality.aqi if weather.air_quality else "N/A",
        }

        return ctx


# Then use them
_renderer: TemplateRenderer = TemplateRenderer()

# Add this constant with type annotation
FULL_REFRESH_INTERVAL: timedelta = timedelta(hours=6)


class WkhtmlToPngRenderer(HtmlRenderer):
    """HTML to PNG renderer using wkhtmltoimage."""

    def __init__(self, width: int = 1872, height: int = 1404) -> None:
        """Initialize the renderer.

        Args:
            width: Output image width
            height: Output image height
        """
        self.width = width
        self.height = height

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
