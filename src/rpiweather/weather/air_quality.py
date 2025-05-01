from __future__ import annotations

from typing import Dict, Optional, ClassVar
from pydantic import BaseModel, Field


class AirQuality(BaseModel):
    """Air quality data model.

    This class represents air quality information from pollution APIs,
    including the Air Quality Index (AQI) and its components.
    """

    # AQI category labels and thresholds
    AQI_CATEGORIES: ClassVar[Dict[int, str]] = {
        1: "Good",
        2: "Fair",
        3: "Moderate",
        4: "Poor",
        5: "Very Poor",
    }

    # Color codes for AQI categories
    AQI_COLORS: ClassVar[Dict[int, str]] = {
        1: "#4CAF50",  # Green
        2: "#8BC34A",  # Light Green
        3: "#FFC107",  # Amber
        4: "#FF9800",  # Orange
        5: "#F44336",  # Red
    }

    # Main AQI information
    aqi: str = Field(..., description="Text representation of air quality")
    aqi_value: int = Field(..., ge=1, le=5, description="Numeric AQI value (1-5)")

    # Optional component concentrations (μg/m³)
    components: Optional[Dict[str, float]] = Field(
        None, description="Air pollutant concentrations"
    )

    @property
    def color(self) -> str:
        """Get the color code associated with this AQI level.

        Returns:
            Hex color code (e.g., "#4CAF50")
        """
        return self.AQI_COLORS.get(self.aqi_value, "#9E9E9E")  # Default gray

    @property
    def description(self) -> str:
        """Get a human-readable description of air quality.

        Returns:
            Description string including AQI level
        """
        return f"Air Quality: {self.aqi} ({self.aqi_value}/5)"

    def get_component_name(self, code: str) -> str:
        """Convert component code to human-readable name.

        Args:
            code: Component code (e.g., "pm25", "o3")

        Returns:
            Human-readable name (e.g., "PM2.5", "Ozone")
        """
        component_names = {
            "co": "Carbon Monoxide",
            "no": "Nitrogen Monoxide",
            "no2": "Nitrogen Dioxide",
            "o3": "Ozone",
            "so2": "Sulfur Dioxide",
            "pm2_5": "PM2.5",
            "pm10": "PM10",
            "nh3": "Ammonia",
        }
        return component_names.get(code, code)

    @classmethod
    def from_aqi_value(cls, value: int) -> AirQuality:
        """Create an AirQuality instance from just an AQI value.

        Args:
            value: AQI value (1-5)

        Returns:
            AirQuality instance

        Raises:
            ValueError: If value is outside valid range
        """
        if value < 1 or value > 5:
            raise ValueError(f"AQI value must be between 1-5, got {value}")

        category = cls.AQI_CATEGORIES.get(value, "Unknown")
        return cls(
            aqi=category,
            aqi_value=value,
            components=None,  # Add this line to fix the error
        )

    @classmethod
    def not_available(cls) -> AirQuality:
        """Create an AirQuality instance for when data is not available."""
        return cls(
            aqi="N/A",
            aqi_value=1,  # Use a valid value within the allowed range
            components=None,  # Explicitly set components to None
        )
