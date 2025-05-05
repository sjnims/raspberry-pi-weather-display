"""Weather unit conversion utilities."""

from __future__ import annotations

from typing import ClassVar


class UnitConverter:
    """Weather unit conversion utilities.

    Converts between different measurement systems (metric/imperial) and
    provides formatted representations for:
    - Temperature (°C/°F)
    - Wind speed (m/s, km/h, mph)
    - Pressure (hPa, inHg)
    - Precipitation (mm, in)

    Also includes conversions to user-friendly formats like
    cardinal directions and Beaufort scale.
    """

    # Wind direction constants
    DIRECTIONS: ClassVar[list[str]] = [
        "N",
        "NNE",
        "NE",
        "ENE",
        "E",
        "ESE",
        "SE",
        "SSE",
        "S",
        "SSW",
        "SW",
        "WSW",
        "W",
        "WNW",
        "NW",
        "NNW",
    ]

    # Beaufort scale thresholds (mph)
    BEAUFORT_LIMITS: ClassVar[list[int]] = [1, 4, 7, 12, 18, 24, 31, 38, 46, 54, 63, 73]

    @staticmethod
    def mm_to_inches(mm: float) -> float:
        """Convert millimeters to inches (2 dp)."""
        return round(mm / 25.4, 2)

    @staticmethod
    def hpa_to_inhg(hpa: float) -> float:
        """Convert pressure hPa → inches Hg (2 dp)."""
        return round(hpa * 0.02953, 2)

    @classmethod
    def deg_to_cardinal(cls, deg: float) -> str:
        """Convert wind bearing to 16-point compass direction."""
        return cls.DIRECTIONS[int((deg % 360) / 22.5 + 0.5) % 16]

    @classmethod
    def beaufort_from_speed(cls, speed_mph: float) -> int:
        """Convert wind speed to Beaufort scale (0-12)."""
        for bft, lim in enumerate(cls.BEAUFORT_LIMITS):
            if speed_mph < lim:
                return bft
        return 12
