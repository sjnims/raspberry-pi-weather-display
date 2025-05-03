"""Precipitation data processing utilities."""

from __future__ import annotations

from typing import Any, Mapping, Optional

from rpiweather.types.weather import PrecipObj
from rpiweather.weather.utils.units import UnitConverter


class PrecipitationUtils:
    """Utilities for processing precipitation forecast data.

    Provides methods to calculate precipitation probability and amounts,
    determine precipitation types (rain, snow, etc.), and format
    precipitation data for display.
    """

    @staticmethod
    def get_one_hour_amt(mapping: Optional[Mapping[str, Any]]) -> float:
        """Extract 1-hour precipitation amount from data structure."""
        if mapping is None:
            return 0.0
        try:
            return float(mapping.get("1h", 0) or 0)
        except (TypeError, ValueError):
            return 0.0

    @classmethod
    def hourly_precip(
        cls,
        hour: Mapping[str, Any] | PrecipObj,
        imperial: bool = False,
    ) -> str:
        """Format hourly precipitation amount (rain or snow)."""
        if isinstance(hour, Mapping):
            rain_amt = cls.get_one_hour_amt(hour.get("rain"))
            snow_amt = cls.get_one_hour_amt(hour.get("snow"))
        else:
            rain_amt = cls.get_one_hour_amt(getattr(hour, "rain", None))
            snow_amt = cls.get_one_hour_amt(getattr(hour, "snow", None))

        amount: float = rain_amt or snow_amt
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
