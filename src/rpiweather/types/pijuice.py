"""Type definitions for PiJuice hardware interface."""

from typing import Any, Protocol, TypedDict, runtime_checkable


class RTCData(TypedDict):
    """PiJuice RTC time data."""

    year: int
    month: int
    day: int
    hour: int
    minute: int
    second: int


class RTCResult(TypedDict):
    """Result from RTC methods."""

    data: RTCData


class StatusResult(TypedDict):
    """Result from status methods."""

    data: int


class BatteryStatusDict(TypedDict, total=False):
    """Battery status information dictionary."""

    charge_level: int
    is_charging: bool
    is_discharging: bool
    voltage: float


class PiJuiceStatusDict(TypedDict):
    """PiJuice status information dictionary."""

    battery: BatteryStatusDict


@runtime_checkable
class RTCInterface(Protocol):
    """Protocol for PiJuice RTC interface."""

    def GetTime(self) -> dict[str, Any]: ...
    def SetTime(self, time_dict: dict[str, int] | None = None) -> dict[str, Any]: ...
    def SetWakeup(self, epoch_time: int) -> dict[str, Any]: ...


@runtime_checkable
class StatusInterface(Protocol):
    """Protocol for PiJuice status API."""

    def GetStatus(self) -> dict[str, Any]: ...
    def GetChargeLevel(self) -> dict[str, int]: ...
    def GetBatteryTemperature(self) -> dict[str, float]: ...


@runtime_checkable
class PiJuiceLike(Protocol):
    """Protocol for objects that behave like PiJuice."""

    status: StatusInterface
    rtc: RTCInterface
