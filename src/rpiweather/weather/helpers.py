from __future__ import annotations
from typing import Dict, Any

_DIRECTIONS = [
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


def deg_to_cardinal(deg: float) -> str:
    """Convert wind bearing to 16-point compass."""
    return _DIRECTIONS[int((deg % 360) / 22.5 + 0.5) % 16]


def beaufort_from_speed(speed_mph: float) -> int:
    """Return Beaufort number 0-12 for a speed in mph."""
    limits = [1, 4, 7, 12, 18, 24, 31, 38, 46, 54, 63, 73]
    for bft, lim in enumerate(limits):
        if speed_mph < lim:
            return bft
    return 12


def owm_icon_class(weather_item: Dict[str, Any]) -> str:
    """Map an OpenWeather `weather` element to Weather-Icons CSS class."""
    wid = weather_item["id"]
    variant = "night" if weather_item["icon"].endswith("n") else "day"
    return f"wi-owm-{variant}-{wid}"


def hourly_precip(hour: Dict[str, Any]) -> str:
    """Return precipitation amount as string, or empty string if none."""
    amount = hour.get("rain", {}).get("1h", 0) or hour.get("snow", {}).get("1h", 0)
    return str(round(amount, 2)) if amount > 0 else ""


def moon_phase_icon(phase: float) -> str:
    """
    Convert OpenWeather moon_phase value (0-1) to Weather Icons class name.
    Uses the "alt" moon icon variants with circular outlines.

    OpenWeather API provides moon phase as a single float from 0-1:
    0: New Moon
    0.25: First Quarter
    0.5: Full Moon
    0.75: Last Quarter
    """
    phases = [
        "wi-moon-alt-new",  # 0
        "wi-moon-alt-waxing-crescent-1",  # 0.04
        "wi-moon-alt-waxing-crescent-2",  # 0.08
        "wi-moon-alt-waxing-crescent-3",  # 0.12
        "wi-moon-alt-waxing-crescent-4",  # 0.16
        "wi-moon-alt-waxing-crescent-5",  # 0.20
        "wi-moon-alt-waxing-crescent-6",  # 0.24
        "wi-moon-alt-first-quarter",  # 0.25
        "wi-moon-alt-waxing-gibbous-1",  # 0.29
        "wi-moon-alt-waxing-gibbous-2",  # 0.33
        "wi-moon-alt-waxing-gibbous-3",  # 0.37
        "wi-moon-alt-waxing-gibbous-4",  # 0.41
        "wi-moon-alt-waxing-gibbous-5",  # 0.45
        "wi-moon-alt-waxing-gibbous-6",  # 0.49
        "wi-moon-alt-full",  # 0.5
        "wi-moon-alt-waning-gibbous-1",  # 0.54
        "wi-moon-alt-waning-gibbous-2",  # 0.58
        "wi-moon-alt-waning-gibbous-3",  # 0.62
        "wi-moon-alt-waning-gibbous-4",  # 0.66
        "wi-moon-alt-waning-gibbous-5",  # 0.70
        "wi-moon-alt-waning-gibbous-6",  # 0.74
        "wi-moon-alt-third-quarter",  # 0.75
        "wi-moon-alt-waning-crescent-1",  # 0.79
        "wi-moon-alt-waning-crescent-2",  # 0.83
        "wi-moon-alt-waning-crescent-3",  # 0.87
        "wi-moon-alt-waning-crescent-4",  # 0.91
        "wi-moon-alt-waning-crescent-5",  # 0.95
        "wi-moon-alt-waning-crescent-6",  # 0.99
    ]
    index = min(int(phase * 28), 27)  # Ensure index is within bounds
    return phases[index]
