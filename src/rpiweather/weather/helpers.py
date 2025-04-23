from __future__ import annotations

from typing import Any, Mapping
from typing import Protocol, runtime_checkable


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


def owm_icon_class(weather_item: Mapping[str, Any] | _WeatherObj) -> str:  # noqa: D401
    """Return the Weather Icons CSS class for an OpenWeather *weather* entry.

    The helper accepts either a raw ``Mapping`` from the JSON API **or** the
    typed ``WeatherCondition`` model that we surface elsewhere.  A small
    ``Protocol`` (``_WeatherObj``) lets *pyright --strict* understand the
    attribute access without resorting to ``Any``.
    """

    if isinstance(weather_item, Mapping):
        wid_str: str = str(weather_item["id"])
        icon_str: str = str(weather_item["icon"])
    else:  # _WeatherObj path – protected by runtime_checkable
        wid_str = str(weather_item.id)
        icon_str = str(weather_item.icon)

    variant: str = "night" if icon_str.endswith("n") else "day"
    return f"wi-owm-{variant}-{wid_str}"


def _one_hour_amt(mapping: Mapping[str, Any] | None) -> float:
    """Return the 1-hour precip amount from an OpenWeather sub‑dict."""
    if mapping is None:
        return 0.0
    try:
        return float(mapping.get("1h", 0) or 0)
    except (TypeError, ValueError):
        return 0.0


def hourly_precip(hour: Mapping[str, Any] | _PrecipObj) -> str:  # noqa: D401
    """
    Extract the 1-hour precipitation amount (rain or snow) from an *hourly*
    or *current* entry.  Accepts either the raw ``Mapping`` from the JSON
    response *or* a typed Pydantic model instance.
    """

    if isinstance(hour, Mapping):
        rain_amt = _one_hour_amt(hour.get("rain"))  # type: ignore[arg-type]
        snow_amt = _one_hour_amt(hour.get("snow"))  # type: ignore[arg-type]
    else:  # _PrecipObj path – protected by runtime_checkable
        rain_amt = _one_hour_amt(getattr(hour, "rain", None))  # type: ignore[arg-type]
        snow_amt = _one_hour_amt(getattr(hour, "snow", None))  # type: ignore[arg-type]

    amount = rain_amt or snow_amt
    return f"{amount:.2f}" if amount > 0 else ""


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
