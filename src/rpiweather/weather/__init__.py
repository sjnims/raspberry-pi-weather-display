"""Weather package - holds API client, helpers, and custom errors."""

__version__ = "0.1.0"

from rpiweather.system.utils import BatteryUtils
from rpiweather.types import PiJuiceLike

from .air_quality import AirQuality
from .api import WeatherAPI
from .errors import NetworkError, ParseError, WeatherAPIError
from .models import Current, Daily, Hourly, WeatherResponse
from .utils import (
    PrecipitationUtils,
    UnitConverter,
    WeatherIcons,
)

# Define what gets imported with: from rpiweather.weather import *
__all__ = [
    "AirQuality",
    "BatteryUtils",
    "Current",
    "Daily",
    "Hourly",
    "NetworkError",
    "ParseError",
    "PiJuiceLike",
    "PrecipitationUtils",
    "UnitConverter",
    "WeatherAPI",
    "WeatherAPIError",
    "WeatherIcons",
    "WeatherResponse",
]
