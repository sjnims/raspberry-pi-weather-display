# src/rpiweather/display/protocols.py
from __future__ import annotations
from pathlib import Path
from typing import Protocol, runtime_checkable
from rpiweather.constants import RefreshMode


class HtmlRenderer(Protocol):
    """Protocol for HTML to image rendering."""

    def render_to_image(self, html: str, output_path: Path) -> None:
        """Render HTML to an image file.

        Args:
            html: HTML content to render
            output_path: Path where the image will be saved
        """
        ...


@runtime_checkable
class Display(Protocol):
    """Protocol defining the interface for display devices."""

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
