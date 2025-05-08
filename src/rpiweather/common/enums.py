from enum import Enum


class RefreshMode(Enum):
    """Display refresh modes for e-paper displays.

    Different refresh modes offer tradeoffs between image quality, refresh speed,
    and power consumption. The optimal mode depends on display content and
    battery considerations.
    """

    FULL = 0  # Full white-black-white refresh (highest quality, slowest)
    GREYSCALE = 2  # 16-level greyscale refresh (GC16, balanced mode)
