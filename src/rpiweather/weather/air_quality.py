from __future__ import annotations

from pydantic import BaseModel


class AirQuality(BaseModel):
    aqi: str
    aqi_value: int
