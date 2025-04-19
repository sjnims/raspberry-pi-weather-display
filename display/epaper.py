from __future__ import annotations
from pathlib import Path
from typing import Final
import logging

try:
    from waveshare_epaper_it8951 import IT8951 as it8951_epd # type: ignore
except ImportError:
    it8951_epd = None

WIDTH: Final = 1872
HEIGHT: Final = 1404

# GC16 (mode 2) = 16‑level greyscale.  mode 0 is a full white‑black‑white cycle
MODE_GC16: Final = 2
VCOM_VOLTS: Final = -1.45  # factory sticker on the panel


def display_png(
    png_path: Path,
    simulate: bool | None = None,
    *,
    mode_override: int | None = None,
) -> None:
    """
    Render a pre-rasterised PNG to the IT8951 panel.

    Parameters
    ----------
    png_path : Path
        File to display (1872x1404 PNG).
    simulate : bool | None
        If True, skip hardware access and just print a stub message.  Defaults
        to auto-detect (True when import fails).
    mode_override : int | None
        Force a specific IT8951 LUT mode.  None => GC16 (mode 2).
        Use 0 for a full white-black-white refresh to scrub ghosting.
    """
    if simulate is None:
        simulate = it8951_epd is None

    if simulate:
        print(
            f"[SIM] Would display {png_path} "
            f"(mode {mode_override or MODE_GC16}, VCOM {VCOM_VOLTS} V)"
        )
        return

    # Assertion to help the type checker understand that IT8951 cannot be None here
    assert (
        it8951_epd is not None
    ), "IT8951 module must be available when not in simulation mode"

    epd = it8951_epd() # type: ignore
    epd.init() # type: ignore

    # Set VCOM to factory-specified value.  Newer drivers take mV, older take V.
    try:
        epd.set_vcom(int(VCOM_VOLTS * 1000))  # type: ignore # millivolts
    except (AttributeError, TypeError):
        epd.set_vcom(VCOM_VOLTS)  # type: ignore # volts

    # Log the read-back VCOM for verification
    try:
        logging.getLogger("weather_display").debug(
            "VCOM set to %.2f V (panel reports %.2f V)",
            VCOM_VOLTS,
            epd.get_vcom() / 1000, # type: ignore
        )
    except Exception:
        pass

    mode = mode_override or MODE_GC16
    epd.display(png_path.as_posix(), ROTATE_0=True, mode=mode) # type: ignore
    epd.sleep() # type: ignore
