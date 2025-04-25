from __future__ import annotations

import csv
from typing import Any, Mapping, Protocol, runtime_checkable, TypedDict


OWM_ICON_MAP: dict[str, str] = {}


class BatteryStatusDict(TypedDict, total=False):
    charge_level: int
    is_charging: bool
    is_discharging: bool
    voltage: float


class PiJuiceStatusDict(TypedDict):
    battery: BatteryStatusDict


@runtime_checkable
class PiJuiceLike(Protocol):
    class StatusAPI(Protocol):
        def GetStatus(self) -> PiJuiceStatusDict: ...
        def GetChargeLevel(self) -> dict[str, int]: ...
        def GetBatteryTemperature(self) -> dict[str, float]: ...

    status: StatusAPI


def load_icon_mapping(path: str = "owm_icon_map.csv") -> None:
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
            OWM_ICON_MAP[key] = row["Weather Icons Filename"].strip()


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


def get_weather_icon_filename(weather_item: Mapping[str, Any] | _WeatherObj) -> str:
    """
    Return the Weather Icons SVG filename for an OpenWeather *weather* entry.

    This uses a lookup table (loaded from CSV) to map OWM condition `id` and `icon`
    to the correct `wi-*.svg` icon. Handles special cases like day/night variants
    for ids 800-804 (based on the `icon` suffix 'd' or 'n').

    Example output: 'wi-day-sunny.svg' or 'wi-night-clear.svg'
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
    return OWM_ICON_MAP.get(key, "wi-na.svg")


def get_battery_status(pijuice: PiJuiceLike) -> dict[str, Any]:
    """
    Get the current battery status from the PiJuice object.
    Returns a dictionary with keys: 'charge_level', 'is_charging', 'is_discharging', 'battery_voltage'.
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


# ── unit‑conversion helpers ──────────────────────────────────────────────
def mm_to_inches(mm: float) -> float:
    """Convert millimetres to inches (2 dp)."""
    return round(mm / 25.4, 2)


def hpa_to_inhg(hpa: float) -> float:
    """Convert pressure hPa → inches Hg (2 dp)."""
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


def _one_hour_amt(mapping: Mapping[str, Any] | None) -> float:
    """Return the 1-hour precip amount from an OpenWeather sub-dict."""
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


def get_moon_phase_icon_filename(phase: float) -> str:
    """
    Convert OpenWeather moon_phase value (0-1) to Weather Icons moon phase file name.
    Uses the "alt" moon icon variants with circular outlines.

    OpenWeather API provides moon phase as a single float from 0-1:
    0: New Moon
    0.25: First Quarter
    0.5: Full Moon
    0.75: Last Quarter
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


def get_moon_phase_label(phase: float) -> str:
    """
    Convert OpenWeather moon_phase float (0.0-1.0) to a human-readable phase label.
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
