from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class SystemStatus:
    """Represents the current status of the system hardware.

    This class encapsulates all system-related information including
    battery status, charging state, and resource utilization.
    """

    # Battery information
    soc: int  # State of charge (percentage)
    is_charging: bool
    battery_warning: bool = False
    voltage: Optional[float] = None

    # System information
    last_update: datetime = datetime.now()

    @property
    def critical_battery(self) -> bool:
        """Return True if battery level is critically low."""
        return self.soc <= 10

    @property
    def low_battery(self) -> bool:
        """Return True if battery level is low but not critical."""
        return 10 < self.soc <= 25

    @property
    def formatted_soc(self) -> str:
        """Return formatted battery percentage string."""
        return f"{self.soc}%"
