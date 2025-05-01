"""Weather package - holds API client, helpers, and custom errors."""

__version__ = "0.1.0"

# Re-export key classes and functions for cleaner imports
from .models import WeatherResponse, Current, Hourly, Daily
from .air_quality import AirQuality
from .errors import WeatherAPIError, NetworkError, ParseError
from .api import WeatherAPI, fetch_weather, build_context

# Import common helper functions
from .helpers import (
    get_weather_icon_filename,
    deg_to_cardinal,
    beaufort_from_speed,
    hourly_precip,
    get_moon_phase_icon_filename,
    get_moon_phase_label,
    load_icon_mapping,
    get_battery_status,  # Add this line
    PiJuiceLike,  # Add this import
)

# Define what gets imported with: from rpiweather.weather import *
__all__ = [
    # Main API
    "WeatherAPI",
    "fetch_weather",
    "build_context",
    # Models
    "WeatherResponse",
    "Current",
    "Hourly",
    "Daily",
    "AirQuality",
    # Errors
    "WeatherAPIError",
    "NetworkError",
    "ParseError",
    # Helpers
    "get_weather_icon_filename",
    "deg_to_cardinal",
    "beaufort_from_speed",
    "hourly_precip",
    "get_moon_phase_icon_filename",
    "get_moon_phase_label",
    "load_icon_mapping",
    "get_battery_status",  # Add this
    "PiJuiceLike",  # Add this to the __all__ list
]
