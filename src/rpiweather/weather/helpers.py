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


#
# ── unit‑conversion helpers ──────────────────────────────────────────────
def mm_to_inches(mm: float) -> float:
    """Convert millimetres to inches (2 dp)."""
    return round(mm / 25.4, 2)


def hpa_to_inhg(hpa: float) -> float:
    """Convert pressure hPa → inches Hg (2 dp)."""
    return round(hpa * 0.02953, 2)


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


def get_weather_icon_filename(weather_item: Mapping[str, Any] | _WeatherObj) -> str:
    """
    Return the Weather Icons SVG filename for an OpenWeather *weather* entry.

    Accepts either a raw Mapping from the JSON API or a typed WeatherCondition model.

    Example output: 'wi-night-rain.svg' or 'wi-day-clear.svg'
    """
    if isinstance(weather_item, Mapping):
        # Main is the textual description of the weather condition
        # (e.g. "clear sky", "light rain", etc.) and icon is the OpenWeather
        # icon code (e.g. "01d", "02n", etc.).  The icon code is a 2-character
        # string where the first character is a number (0-9) and the second
        # character is either "d" (day) or "n" (night).
        main = str(weather_item.get("main", "")).lower().replace(" ", "-")
        icon = str(weather_item.get("icon", ""))
    else:  # _WeatherObj path – protected by runtime_checkable
        main = str(getattr(weather_item, "main", "")).lower().replace(" ", "-")
        icon = str(getattr(weather_item, "icon", ""))

    if not main:
        return "wi-unknown.svg"

    if icon.endswith("d"):
        variant = "day"
    elif icon.endswith("n"):
        variant = "night"
    else:
        variant = None

    if variant:
        return f"wi-{variant}-{main}.svg"
    else:
        return f"wi-{main}.svg"


def _one_hour_amt(mapping: Mapping[str, Any] | None) -> float:
    """Return the 1-hour precip amount from an OpenWeather sub‑dict."""
    if mapping is None:
        return 0.0
    try:
        return float(mapping.get("1h", 0) or 0)
    except (TypeError, ValueError):
        return 0.0


def hourly_precip(
    hour: Mapping[str, Any] | _PrecipObj,
    imperial: bool = False,
) -> str:  # noqa: D401
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
    if amount <= 0:
        return ""
    if imperial:
        amount = mm_to_inches(amount)
    return f"{amount:.2f}"


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
