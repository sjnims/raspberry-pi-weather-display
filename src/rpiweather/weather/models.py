"""Typed models for OpenWeather OneCall 3.0 responses.

Only the fields used by the dashboard are modelled for now; add more as needed.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from pydantic import BaseModel, Field, field_validator


# ─────────────────────────── primitives ──────────────────────────────────────


class Coord(BaseModel):
    lat: float
    lon: float


class WeatherCondition(BaseModel):
    id: int
    main: str
    description: str
    icon: str


# ─────────────────────────── composite blocks ────────────────────────────────


class Current(BaseModel):
    dt: datetime
    sunrise: datetime
    sunset: datetime
    temp: float
    feels_like: float = Field(..., alias="feels_like")
    pressure: int
    humidity: int
    wind_speed: float
    wind_deg: int
    weather: List[WeatherCondition]

    # convert POSIX seconds → UTC datetime
    @field_validator("dt", "sunrise", "sunset", mode="before")
    @classmethod
    def _ts_to_dt(cls, v: int) -> datetime:  # noqa: D401
        return datetime.fromtimestamp(v, tz=timezone.utc)


class Hourly(BaseModel):
    dt: datetime
    temp: float
    weather: List[WeatherCondition]

    @field_validator("dt", mode="before")
    @classmethod
    def _ts_to_dt(cls, v: int) -> datetime:
        return datetime.fromtimestamp(v, tz=timezone.utc)


class DailyTemp(BaseModel):
    day: float
    night: float
    eve: float
    morn: float
    min: float
    max: float


class Daily(BaseModel):
    dt: datetime
    sunrise: datetime
    sunset: datetime
    temp: DailyTemp
    weather: List[WeatherCondition]

    @field_validator("dt", "sunrise", "sunset", mode="before")
    @classmethod
    def _dt_to_dt(cls, v: int) -> datetime:
        return datetime.fromtimestamp(v, tz=timezone.utc)


# ─────────────────────────── top‑level response ──────────────────────────────


class WeatherResponse(BaseModel):
    lat: float
    lon: float
    timezone: str
    timezone_offset: int
    current: Current
    hourly: List[Hourly]
    daily: List[Daily]
