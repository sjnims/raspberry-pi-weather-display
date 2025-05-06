# src/rpiweather/system/__init__.py
"""System module for hardware status and interaction."""

# Re-export commonly used classes for cleaner imports
from rpiweather.system.power import BatteryManager, BatteryUtils, PowerManager, QuietHoursHelper
from rpiweather.system.remote import create_wake_state_provider
from rpiweather.system.status import SystemStatus

# Define the public API
__all__ = [
    "BatteryManager",
    "BatteryUtils",
    "PowerManager",
    "QuietHoursHelper",
    "SystemStatus",
    "create_wake_state_provider",
]
