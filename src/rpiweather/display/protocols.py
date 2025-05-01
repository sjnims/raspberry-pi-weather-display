# src/rpiweather/display/protocols.py
from __future__ import annotations
from pathlib import Path
from typing import Protocol, runtime_checkable


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

    def display_image(self, image_path: Path, full_refresh: bool = False) -> None:
        """Display an image on the device.

        Args:
            image_path: Path to the image file
            full_refresh: If True, perform a full refresh cycle
        """
        ...
