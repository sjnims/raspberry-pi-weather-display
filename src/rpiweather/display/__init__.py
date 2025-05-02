"""Display package - holds display functionalities and components."""

from rpiweather.display.error_ui import render_error_screen
from rpiweather.display.protocols import Display
from rpiweather.display.epaper import (
    IT8951Display,
    WIDTH,
    HEIGHT,
)

__all__ = ["Display", "IT8951Display", "WIDTH", "HEIGHT", "render_error_screen"]
