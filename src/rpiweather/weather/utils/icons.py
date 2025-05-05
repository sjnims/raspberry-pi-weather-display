"""Weather icon utilities and mappings."""

from __future__ import annotations

import csv
from collections.abc import Mapping
from typing import Any, ClassVar

from rpiweather.types.weather import WeatherObj


class WeatherIcons:
    """Weather icon mapping and retrieval utilities.

    Maps OpenWeatherMap condition codes to icon filenames,
    handles special cases like day/night variations, and
    provides helper methods for moon phase icons.
    """

    # Class variable to store the icon mapping
    _icon_map: ClassVar[dict[str, str]] = {}

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
    def get_icon_filename(cls, weather_item: Mapping[str, Any] | WeatherObj) -> str:
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

        key = f"{owm_id}{icon[-1]}" if owm_id in {"800", "801", "802", "803", "804"} else owm_id
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
    def get_icon_map(cls) -> dict[str, str]:
        """Get the complete icon mapping dictionary."""
        return cls._icon_map
