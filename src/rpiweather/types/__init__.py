"""Type definitions for rpiweather."""

from .pijuice import (
    BatteryStatusDict,
    PiJuiceStatusDict,
    RTCInterface,
    StatusInterface,
    PiJuiceLike,
)

from .weather import WeatherObj, PrecipObj

__all__ = [
    "BatteryStatusDict",
    "PiJuiceStatusDict",
    "RTCInterface",
    "StatusInterface",
    "PiJuiceLike",
    "WeatherObj",
    "PrecipObj",
]
