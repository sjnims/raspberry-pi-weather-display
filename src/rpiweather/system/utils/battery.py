"""Battery management utilities."""

from __future__ import annotations

from typing import Any

from rpiweather.types.pijuice import PiJuiceLike


class BatteryUtils:
    """Utilities for battery status management."""

    @staticmethod
    def get_battery_status(pijuice: PiJuiceLike) -> dict[str, Any]:
        """Get comprehensive battery status information.

        Args:
            pijuice: PiJuice or compatible object

        Returns:
            Dictionary with battery status information
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
