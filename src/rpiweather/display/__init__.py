"""Display package - holds display functionalities and components."""

from rpiweather.display.protocols import Display
from rpiweather.display.epaper import (
    IT8951Display,
    WIDTH,
    HEIGHT,
)

__all__ = ["Display", "IT8951Display", "WIDTH", "HEIGHT"]
