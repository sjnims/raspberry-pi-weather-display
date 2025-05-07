"""Display-specific formatting utilities."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from rpiweather.types.weather import PrecipObj
from rpiweather.weather import PrecipitationUtils
from rpiweather.weather.utils.units import UnitConverter


def wind_direction_angle(deg: float | None) -> str:
    """Convert wind bearing to CSS custom property value.

    Args:
        deg: Wind direction in degrees (0 = N, 90 = E, etc.) or None

    Returns:
        CSS angle value for wind direction arrow (e.g. "180deg")
    """
    if deg is None:
        return "0deg"
    return f"{(deg + 180) % 360}deg"


def format_precip(
    hour: Mapping[str, Any] | PrecipObj,
    imperial: bool = False,
) -> str:
    """Format hourly precipitation amount (rain or snow)."""
    amount: float = PrecipitationUtils.get_precipitation_amount(hour)
    if amount <= 0:
        return ""
    if imperial:
        amount = UnitConverter.mm_to_inches(amount)
        rounded = round(amount, 2)
        s = str(rounded)
        # Remove trailing zeros and dot if needed (e.g. 0.10 -> 0.1, 0.00 -> "")
        if "." in s:
            s = s.rstrip("0").rstrip(".")
        return s
    return f"{amount:.2f}"
