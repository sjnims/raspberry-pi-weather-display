from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class SystemStatus:
    """System hardware status information.

    Provides information about the Raspberry Pi's current hardware state,
    particularly battery-related metrics:
    - Battery state of charge (percentage)
    - Charging status
    - Warning flags for low battery conditions

    This information is displayed in the dashboard UI and used for
    power management decisions.
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
