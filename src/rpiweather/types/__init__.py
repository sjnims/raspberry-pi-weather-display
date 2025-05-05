"""Type definitions for rpiweather."""

from .pijuice import (
    BatteryStatusDict,
    PiJuiceLike,
    PiJuiceStatusDict,
    RTCInterface,
    StatusInterface,
)
from .weather import PrecipObj, WeatherObj

__all__ = [
    "BatteryStatusDict",
    "PiJuiceLike",
    "PiJuiceStatusDict",
    "PrecipObj",
    "RTCInterface",
    "StatusInterface",
    "WeatherObj",
]
