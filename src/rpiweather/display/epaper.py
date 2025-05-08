from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops

from rpiweather.display.protocols import DisplayDriver
from rpiweather.settings.application import RefreshMode, UserSettings


class IT8951Display(DisplayDriver):
    """IT8951 E-Paper display handler.

    This class manages interactions with the IT8951 e-paper display,
    providing graceful degradation when hardware isn't available.
    """

    def __init__(self, simulate: bool = False, epd_driver: Any | None = None) -> None:
        """Initialize the display handler.

        Args:
            simulate: If True, run in simulation mode without hardware
            epd_driver: Optional pre-configured EPD driver (useful for testing)
        """
        self.logger = logging.getLogger("weather_display")
        self.simulate = simulate
        self._epd: Any | None = epd_driver
        self.settings = UserSettings.load()
        self.vcom = self.settings.vcom_volts

        # Use dimensions from settings if available, otherwise use defaults
        self.width: int = getattr(self.settings, "display_width", 1872)
        self.height: int = getattr(self.settings, "display_height", 1404)

        if not simulate and self._epd is None:
            try:
                # Import the hardware library only when needed
                from waveshare_epaper_it8951 import IT8951  # type: ignore[import]

                self._epd = IT8951()
                self.logger.debug("IT8951 display initialized")
            except ImportError:
                self.logger.warning("IT8951 module not found, running in simulation mode")
                self.simulate = True

        self._last_displayed_image: Path | None = None
        self._last_refresh_mode: RefreshMode | None = None
        self._clear_called: bool = False

    def _apply_vcom(self) -> None:
        """Set VCOM to factory-specified value, handling driver differences."""

        assert self._epd is not None
        try:
            # Newer drivers take millivolts
            self._epd.set_vcom(int(self.vcom * 1000))
        except (AttributeError, TypeError):
            # Older drivers take volts
            self._epd.set_vcom(self.vcom)
        # Log the read-back VCOM for verification
        try:
            vcom_reported = self._epd.get_vcom() / 1000
            self.logger.debug(
                "VCOM set to %.2f V (panel reports %.2f V)",
                self.vcom,
                vcom_reported,
            )
        except Exception:
            pass

    def display_image(
        self,
        image_path: Path,
        mode: RefreshMode = RefreshMode.GREYSCALE,
    ) -> None:
        """Display an image on the IT8951 panel.

        Args:
            image_path: Path to the PNG image (1872x1404)
            mode: RefreshMode
                Which refresh mode to use (FULL or GREYSCALE).
        """
        # Track for testing
        self._last_displayed_image = image_path
        self._last_refresh_mode = mode

        mode_value = mode.value

        if self.simulate:
            self.logger.info(
                f"[SIM] Would display {image_path} (mode {mode_value}, VCOM {self.vcom} V)"
            )
            return

        if self._epd is None:
            self.logger.error("Display hardware not initialized")
            return

        # Initialize the display
        self._epd.init()

        self._apply_vcom()

        # Display the image
        self._epd.display(image_path.as_posix(), ROTATE_0=True, mode=mode_value)

        # Put the display to sleep
        self._epd.sleep()

    def get_dimensions(self) -> tuple[int, int]:
        """Return the width and height of the display in pixels.

        Returns:
            Tuple of (width, height) in pixels
        """
        return (self.width, self.height)

    def clear(self) -> None:
        """Clear the display to white."""
        # Track for testing
        self._clear_called = True

        try:
            # First check if _epd exists and is not None
            if self._epd is not None and hasattr(self._epd, "Clear"):
                self._epd.Clear()
                return

            # Alternative: Create a blank white image and display it
            width, height = self.get_dimensions()
            white_image = Image.new("L", (width, height), 255)  # 255 is white

            # Save to a temporary file and display
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp:
                temp_path = Path(temp.name)

            white_image.save(temp_path)
            self.display_image(temp_path, RefreshMode.FULL)
            temp_path.unlink()  # Clean up the temporary file
        except Exception as e:
            self.logger.error(f"Error clearing display: {e}")

    def get_last_displayed_image(self) -> Path | None:
        """Return the path to the last displayed image (for testing)."""
        return self._last_displayed_image

    def get_last_refresh_mode(self) -> RefreshMode | None:
        """Return the last refresh mode used (for testing)."""
        return self._last_refresh_mode

    def was_clear_called(self) -> bool:
        """Return whether clear() was called (for testing)."""
        return self._clear_called

    def reset_test_state(self) -> None:
        """Reset the test state tracking (for testing)."""
        self._last_displayed_image = None
        self._last_refresh_mode = None
        self._clear_called = False


class MockEpdDriver:
    """Mock implementation of the IT8951 driver for testing."""

    def __init__(self):
        self.calls: list[dict[str, Any]] = []

    def init(self) -> None:
        self.calls.append({"method": "init"})

    def sleep(self) -> None:
        self.calls.append({"method": "sleep"})

    def Clear(self) -> None:
        self.calls.append({"method": "Clear"})

    def display(self, image_path: str, ROTATE_0: bool = True, mode: int = 0) -> None:
        self.calls.append(
            {
                "method": "display",
                "image_path": image_path,
                "ROTATE_0": ROTATE_0,
                "mode": mode,
            }
        )

    def set_vcom(self, vcom: int) -> None:
        self.calls.append({"method": "set_vcom", "vcom": vcom})

    def get_vcom(self) -> int:
        self.calls.append({"method": "get_vcom"})
        return 1000  # 1V in millivolts

    def reset_calls(self) -> None:
        self.calls = []


def create_test_display(simulate: bool = True) -> IT8951Display:
    """Create a display instance configured for testing.

    Args:
        simulate: Whether to run in simulation mode

    Returns:
        IT8951Display instance suitable for testing
    """
    if simulate:
        return IT8951Display(simulate=True)
    else:
        mock_driver = MockEpdDriver()
        return IT8951Display(simulate=False, epd_driver=mock_driver)


def compare_display_image(display: IT8951Display, expected_image_path: Path) -> bool:
    """Compare the last displayed image with an expected image.

    Args:
        display: The display instance
        expected_image_path: Path to the expected image

    Returns:
        True if images match, False otherwise
    """
    last_image_path = display.get_last_displayed_image()
    if last_image_path is None:
        return False

    if not os.path.exists(last_image_path):
        return False

    last_image = Image.open(last_image_path)
    expected_image = Image.open(expected_image_path)

    # Convert to same mode if different
    if last_image.mode != expected_image.mode:
        expected_image = expected_image.convert(last_image.mode)

    # Resize if different dimensions
    if last_image.size != expected_image.size:
        # Cast to a known type (tuple of two ints) to satisfy the type checker
        new_size = last_image.size
        expected_image = expected_image.resize(new_size)  # type: ignore

    # Compare images
    diff = ImageChops.difference(last_image, expected_image)

    # If images are identical, diff is all black
    return diff.getbbox() is None
