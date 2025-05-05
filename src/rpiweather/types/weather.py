"""Weather-related type definitions."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class WeatherObj(Protocol):
    """Duck-type for a Pydantic WeatherCondition model (id & icon)."""

    id: int | str
    icon: str


@runtime_checkable
class PrecipObj(Protocol):
    """Duck-type for Hourly/Current models that expose optional rain/snow dicts."""

    rain: Mapping[str, Any] | None
    snow: Mapping[str, Any] | None
