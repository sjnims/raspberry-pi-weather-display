"""Display package – holds display functionalities and components."""

from display.ui import render_error_screen
from display.epaper import display_png

__all__ = ["display_png", "render_error_screen"]
