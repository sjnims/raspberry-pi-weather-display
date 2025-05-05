"""Display package - holds display functionalities and components."""

from rpiweather.display.epaper import (
    IT8951Display,
)
from rpiweather.display.protocols import Display

__all__ = ["Display", "IT8951Display"]
