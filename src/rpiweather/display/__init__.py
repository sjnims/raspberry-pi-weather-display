"""Display package – holds display functionalities and components."""

from rpiweather.display.ui import render_error_screen
from rpiweather.display.epaper import display_png

__all__ = ["display_png", "render_error_screen"]
