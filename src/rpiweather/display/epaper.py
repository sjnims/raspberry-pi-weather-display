from __future__ import annotations
from pathlib import Path
from typing import Optional, Any
import logging

from rpiweather.display.protocols import DisplayDriver
from rpiweather.settings import RefreshMode, UserSettings


class IT8951Display(DisplayDriver):
    """IT8951 E-Paper display handler.

    This class manages interactions with the IT8951 e-paper display,
    providing graceful degradation when hardware isn't available.
    """

    def __init__(self, simulate: bool = False) -> None:
        """Initialize the display handler.

        Args:
            simulate: If True, run in simulation mode without hardware
        """
        self.logger = logging.getLogger("weather_display")
        self.simulate = simulate
        self._epd: Optional[Any] = None
        self.settings = UserSettings.load()
        self.vcom = self.settings.vcom_volts

        if not simulate:
            try:
                # Import the hardware library only when needed
                from waveshare_epaper_it8951 import IT8951  # type: ignore

                self._epd = IT8951()
                self.logger.debug("IT8951 display initialized")
            except ImportError:
                self.logger.warning(
                    "IT8951 module not found, running in simulation mode"
                )
                self.simulate = True

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
        self, image_path: Path, mode: RefreshMode = RefreshMode.GREYSCALE
    ) -> None:
        """Display an image on the IT8951 panel.

        Args:
            image_path: Path to the PNG image (1872x1404)
            mode: RefreshMode
                Which refresh mode to use (FULL or GREYSCALE).
        """
        mode_value = mode.value

        if self.simulate:
            self.logger.info(
                f"[SIM] Would display {image_path} "
                f"(mode {mode_value}, VCOM {self.vcom} V)"
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
