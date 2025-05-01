"""Weather helper utilities for display and data processing."""

from __future__ import annotations

import csv
from typing import Any, Mapping, Protocol, runtime_checkable, Dict, Optional

from rpiweather.types.pijuice import PiJuiceLike  # Update import


# ------------------------- Type Definitions -------------------------


@runtime_checkable
class _WeatherObj(Protocol):
    """Duck-type for a Pydantic WeatherCondition model (id & icon)."""

    id: int | str
    icon: str


@runtime_checkable
class _PrecipObj(Protocol):
    """Duck-type for Hourly/Current models that expose optional rain/snow dicts."""

    rain: Mapping[str, Any] | None
    snow: Mapping[str, Any] | None


# ------------------------- Icon Utilities -------------------------


class WeatherIcons:
    """Weather icon management and mapping utilities."""

    # Class variable to store the icon mapping
    _icon_map: Dict[str, str] = {}

    @classmethod
    def load_mapping(cls, path: str = "owm_icon_map.csv") -> None:
        """Load weather icon mapping from CSV file.

        Args:
            path: Path to the CSV mapping file
        """
        with open(path, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                owm_id = str(row["API response: id"]).strip()
                icon = row["API response: icon"].strip()
                key = (
                    f"{owm_id}{icon[-1]}"
                    if owm_id in {"800", "801", "802", "803", "804"}
                    else owm_id
                )
                cls._icon_map[key] = row["Weather Icons Filename"].strip()

    @classmethod
    def get_icon_filename(cls, weather_item: Mapping[str, Any] | _WeatherObj) -> str:
        """Get the Weather Icons SVG filename for an OpenWeather weather entry.

        Args:
            weather_item: Weather condition item with id and icon attributes

        Returns:
            SVG filename for the matching weather icon
        """
        if isinstance(weather_item, Mapping):
            owm_id = str(weather_item.get("id", "")).strip()
            icon = str(weather_item.get("icon", "")).strip()
        else:
            owm_id = str(getattr(weather_item, "id", "")).strip()
            icon = str(getattr(weather_item, "icon", "")).strip()

        key = (
            f"{owm_id}{icon[-1]}"
            if owm_id in {"800", "801", "802", "803", "804"}
            else owm_id
        )
        return cls._icon_map.get(key, "wi-na.svg")

    @staticmethod
    def get_moon_phase_icon(phase: float) -> str:
        """Get moon phase icon filename based on phase value (0-1).

        Args:
            phase: Moon phase value (0-1)

        Returns:
            SVG filename for the matching moon phase icon
        """
        phases = [
            "new",  # 0
            "waxing-crescent-1",  # 0.04
            "waxing-crescent-2",  # 0.08
            "waxing-crescent-3",  # 0.12
            "waxing-crescent-4",  # 0.16
            "waxing-crescent-5",  # 0.20
            "waxing-crescent-6",  # 0.24
            "first-quarter",  # 0.25
            "waxing-gibbous-1",  # 0.29
            "waxing-gibbous-2",  # 0.33
            "waxing-gibbous-3",  # 0.37
            "waxing-gibbous-4",  # 0.41
            "waxing-gibbous-5",  # 0.45
            "waxing-gibbous-6",  # 0.49
            "full",  # 0.5
            "waning-gibbous-1",  # 0.54
            "waning-gibbous-2",  # 0.58
            "waning-gibbous-3",  # 0.62
            "waning-gibbous-4",  # 0.66
            "waning-gibbous-5",  # 0.70
            "waning-gibbous-6",  # 0.74
            "third-quarter",  # 0.75
            "waning-crescent-1",  # 0.79
            "waning-crescent-2",  # 0.83
            "waning-crescent-3",  # 0.87
            "waning-crescent-4",  # 0.91
            "waning-crescent-5",  # 0.95
            "waning-crescent-6",  # 0.99
        ]
        index = min(int(phase * 28), 27)  # Ensure index is within bounds
        return f"wi-moon-alt-{phases[index]}.svg"

    @staticmethod
    def get_moon_phase_label(phase: float) -> str:
        """Get human-readable moon phase label.

        Args:
            phase: Moon phase value (0-1)

        Returns:
            Human-readable moon phase description
        """
        labels = [
            "New Moon",
            "Waxing Crescent",
            "First Quarter",
            "Waxing Gibbous",
            "Full Moon",
            "Waning Gibbous",
            "Last Quarter",
            "Waning Crescent",
        ]
        if phase < 0.03 or phase > 0.97:
            return labels[0]  # New Moon
        elif phase < 0.22:
            return labels[1]
        elif phase < 0.28:
            return labels[2]
        elif phase < 0.47:
            return labels[3]
        elif phase < 0.53:
            return labels[4]
        elif phase < 0.72:
            return labels[5]
        elif phase < 0.78:
            return labels[6]
        else:
            return labels[7]

    @classmethod
    def get_icon_map(cls) -> Dict[str, str]:  # Change from int to str
        return cls._icon_map


# ------------------------- Unit Conversion -------------------------


class UnitConverter:
    """Unit conversion utilities for weather measurements."""

    # Wind direction constants
    DIRECTIONS = [
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
    BEAUFORT_LIMITS = [1, 4, 7, 12, 18, 24, 31, 38, 46, 54, 63, 73]

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


# ------------------------- Precipitation Helpers -------------------------


class PrecipitationUtils:
    """Utilities for handling precipitation data."""

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
        hour: Mapping[str, Any] | _PrecipObj,
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
        return f"{amount:.2f}"


# ------------------------- Battery Utilities -------------------------


class BatteryUtils:
    """Utilities for battery status management."""

    @staticmethod
    def get_battery_status(pijuice: PiJuiceLike) -> dict[str, Any]:
        """Get comprehensive battery status information.

        Args:
            pijuice: PiJuice or compatible object

        Returns:
            Dictionary with battery status information
        """
        status = pijuice.status.GetStatus()
        charge_level = status.get("battery", {}).get("charge_level", 0)
        is_charging = status.get("battery", {}).get("is_charging", False)
        is_discharging = status.get("battery", {}).get("is_discharging", False)
        battery_voltage = status.get("battery", {}).get("voltage", 0.0)
        return {
            "charge_level": charge_level,
            "is_charging": is_charging,
            "is_discharging": is_discharging,
            "battery_voltage": battery_voltage,
        }


# ------------------------- Legacy Functions -------------------------

# Keep the original global for backward compatibility
OWM_ICON_MAP = WeatherIcons.get_icon_map()


# Legacy function wrappers for backward compatibility
def load_icon_mapping(path: str = "owm_icon_map.csv") -> None:
    """Load weather icon mapping from CSV file."""
    WeatherIcons.load_mapping(path)


def get_weather_icon_filename(weather_item: Mapping[str, Any] | _WeatherObj) -> str:
    """Get the Weather Icons SVG filename for an OpenWeather weather entry."""
    return WeatherIcons.get_icon_filename(weather_item)


def get_battery_status(pijuice: PiJuiceLike) -> dict[str, Any]:
    """Get the current battery status from the PiJuice object."""
    return BatteryUtils.get_battery_status(pijuice)


def mm_to_inches(mm: float) -> float:
    """Convert millimetres to inches (2 dp)."""
    return UnitConverter.mm_to_inches(mm)


def hpa_to_inhg(hpa: float) -> float:
    """Convert pressure hPa → inches Hg (2 dp)."""
    return UnitConverter.hpa_to_inhg(hpa)


def deg_to_cardinal(deg: float) -> str:
    """Convert wind bearing to 16-point compass."""
    return UnitConverter.deg_to_cardinal(deg)


def beaufort_from_speed(speed_mph: float) -> int:
    """Return Beaufort number 0-12 for a speed in mph."""
    return UnitConverter.beaufort_from_speed(speed_mph)


def hourly_precip(hour: Mapping[str, Any] | _PrecipObj, imperial: bool = False) -> str:
    """Extract the 1-hour precipitation amount (rain or snow)."""
    return PrecipitationUtils.hourly_precip(hour, imperial)


def get_moon_phase_icon_filename(phase: float) -> str:
    """Convert OpenWeather moon_phase value (0-1) to Weather Icons moon phase file name."""
    return WeatherIcons.get_moon_phase_icon(phase)


def get_moon_phase_label(phase: float) -> str:
    """Convert OpenWeather moon_phase float (0.0-1.0) to a human-readable phase label."""
    return WeatherIcons.get_moon_phase_label(phase)
