# src/rpiweather/display/protocols.py
from __future__ import annotations
from pathlib import Path
from typing import Protocol, runtime_checkable
from rpiweather.settings import RefreshMode


class HtmlRenderer(Protocol):
    """Protocol defining the interface for HTML renderers.

    Implementations of this protocol must provide a method to render
    HTML content to an image file at a specified path.
    """

    def render_to_image(self, html: str, output_path: Path) -> None:
        """Render HTML to an image.

        Args:
            html: HTML content to render
            output_path: Path where the image will be saved
        """
        ...


@runtime_checkable
class Display(Protocol):
    """Protocol defining the interface for display devices.

    This protocol abstracts the hardware-specific details of different display
    technologies (e-ink, LCD, etc.) to allow the application to work with
    any compatible display driver.

    Runtime checking allows the application to detect if an object implements
    this protocol at runtime rather than just during type checking.
    """

    def display_image(
        self, image_path: Path, mode: RefreshMode = RefreshMode.GREYSCALE
    ) -> None:
        """Display an image on the device.

        Args:
            image_path: Path to the image file
            mode: RefreshMode
                Which refresh mode to use (FULL or GREYSCALE)
        """
        ...


# Alias for the display protocol, for clearer DI naming
DisplayDriver = Display
