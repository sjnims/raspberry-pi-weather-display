"""Precipitation data processing utilities."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from rpiweather.types.weather import PrecipObj


class PrecipitationUtils:
    """Utilities for processing precipitation forecast data.

    Provides methods to calculate precipitation probability and amounts,
    determine precipitation types (rain, snow, etc.), and format
    precipitation data for display.
    """

    @staticmethod
    def get_one_hour_amt(mapping: Mapping[str, Any] | None) -> float:
        """Extract 1-hour precipitation amount from data structure."""
        if mapping is None:
            return 0.0
        try:
            return float(mapping.get("1h", 0) or 0)
        except (TypeError, ValueError):
            return 0.0

    @classmethod
    def get_precipitation_amount(
        cls,
        hour: Mapping[str, Any] | PrecipObj,
    ) -> float:
        """Format hourly precipitation amount (rain or snow)."""
        if isinstance(hour, Mapping):
            rain_amt = cls.get_one_hour_amt(hour.get("rain"))
            snow_amt = cls.get_one_hour_amt(hour.get("snow"))
        else:
            rain_amt = cls.get_one_hour_amt(getattr(hour, "rain", None))
            snow_amt = cls.get_one_hour_amt(getattr(hour, "snow", None))

        amount: float = rain_amt or snow_amt
        return amount
