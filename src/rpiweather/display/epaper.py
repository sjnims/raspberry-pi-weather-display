from __future__ import annotations
from pathlib import Path
from typing import Final, Optional, Any
import logging

from rpiweather.display.protocols import Display

# Constants
WIDTH: Final = 1872
HEIGHT: Final = 1404
MODE_GC16: Final = 2  # 16-level greyscale
VCOM_VOLTS: Final = -1.45  # factory sticker on the panel


class IT8951Display:
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

    def display_image(self, image_path: Path, full_refresh: bool = False) -> None:
        """Display an image on the IT8951 panel.

        Args:
            image_path: Path to the PNG image (1872x1404)
            full_refresh: If True, use mode 0 for a full refresh cycle
        """
        mode = 0 if full_refresh else MODE_GC16

        if self.simulate:
            self.logger.info(
                f"[SIM] Would display {image_path} "
                f"(mode {mode}, VCOM {VCOM_VOLTS} V)"
            )
            return

        if self._epd is None:
            self.logger.error("Display hardware not initialized")
            return

        # Initialize the display
        self._epd.init()

        # Set VCOM to factory-specified value
        try:
            # Newer drivers take millivolts
            self._epd.set_vcom(int(VCOM_VOLTS * 1000))
        except (AttributeError, TypeError):
            # Older drivers take volts
            self._epd.set_vcom(VCOM_VOLTS)

        # Log the read-back VCOM for verification
        try:
            vcom_reported = self._epd.get_vcom() / 1000
            self.logger.debug(
                f"VCOM set to {VCOM_VOLTS:.2f} V (panel reports {vcom_reported:.2f} V)"
            )
        except Exception:
            pass

        # Display the image
        self._epd.display(image_path.as_posix(), ROTATE_0=True, mode=mode)

        # Put the display to sleep
        self._epd.sleep()


# Factory function for backward compatibility
def create_display(simulate: bool = False) -> Display:
    """Create an appropriate display handler.

    Args:
        simulate: If True, run in simulation mode

    Returns:
        A Display-compatible object
    """
    return IT8951Display(simulate)


# Legacy function for backward compatibility
def display_png(
    png_path: Path,
    simulate: Optional[bool] = None,
    *,
    mode_override: Optional[int] = None,
) -> None:
    """Legacy function to maintain backward compatibility.

    Args:
        png_path: Path to the PNG image
        simulate: If True, run in simulation mode
        mode_override: Display mode (0 for full refresh, 2 for grayscale)
    """
    display = create_display(simulate is True)
    display.display_image(png_path, full_refresh=mode_override == 0)
