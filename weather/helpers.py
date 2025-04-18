from __future__ import annotations

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
    """Convert wind bearing to 16‑point compass."""
    return _DIRECTIONS[int((deg % 360) / 22.5 + 0.5) % 16]


def beaufort_from_speed(speed_mph: float) -> int:
    """Return Beaufort number 0‑12 for a speed in mph."""
    limits = [1, 4, 7, 12, 18, 24, 31, 38, 46, 54, 63, 73]
    for bft, lim in enumerate(limits):
        if speed_mph < lim:
            return bft
    return 12


def owm_icon_class(weather_item: dict) -> str:
    """Map an OpenWeather `weather` element to Weather‑Icons CSS class."""
    wid = weather_item["id"]
    variant = "night" if weather_item["icon"].endswith("n") else "day"
    return f"wi-owm-{variant}-{wid}"


def hourly_precip(hour: dict) -> float:
    return round(
        hour.get("rain", {}).get("1h", 0) or hour.get("snow", {}).get("1h", 0), 2
    )
