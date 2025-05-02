"""Weather package - holds API client, helpers, and custom errors."""

__version__ = "0.1.0"

# Re-export key classes and functions for cleaner imports
from .models import WeatherResponse, Current, Hourly, Daily
from .air_quality import AirQuality
from .errors import WeatherAPIError, NetworkError, ParseError
from .api import WeatherAPI

# Import common helper functions
from .utils import (
    WeatherIcons,
    UnitConverter,
    PrecipitationUtils,
)

from rpiweather.system.utils import BatteryUtils
from rpiweather.types import PiJuiceLike

# Define what gets imported with: from rpiweather.weather import *
__all__ = [
    # Main API
    "WeatherAPI",
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
    "WeatherIcons",
    "UnitConverter",
    "PrecipitationUtils",
    "BatteryUtils",
    "PiJuiceLike",
]
