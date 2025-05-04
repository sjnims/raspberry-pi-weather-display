from typing import Any
from rpiweather.types.pijuice import PiJuiceLike, StatusInterface, RTCInterface
from rpiweather.system.utils.battery import BatteryUtils


class FakeRTC(RTCInterface):
    def SetWakeupEnabled(self, enabled: bool) -> None:
        pass

    def SetWakeupAlarm(
        self, year: int, month: int, day: int, hour: int, minute: int, second: int
    ) -> None:
        pass

    def GetTime(self) -> dict[str, int]:
        return {"hour": 0}

    def SetTime(self, time_dict: dict[str, int] | None = None) -> dict[str, Any]:
        return time_dict or {}

    def SetWakeup(self, epoch_time: int) -> dict[str, Any]:
        return {"wake": epoch_time}

    def ReadTime(self) -> dict[str, int]:
        return {"hour": 0}


class FakeStatus(StatusInterface):
    def GetStatus(self) -> dict[str, Any]:
        return {
            "battery": {
                "charge_level": 85,
                "is_charging": True,
                "is_discharging": False,
                "voltage": 3.7,
            }
        }

    def GetChargeLevel(self) -> dict[str, int]:
        return {"data": 85}

    def GetBatteryTemperature(self) -> dict[str, float]:
        return {"data": 25.0}


class FakePiJuice(PiJuiceLike):
    status: StatusInterface
    rtc: RTCInterface

    def __init__(self) -> None:
        self.status = FakeStatus()
        self.rtc = FakeRTC()  # placeholder to satisfy protocol


def test_get_battery_status_extracts_fields() -> None:
    result = BatteryUtils.get_battery_status(FakePiJuice())
    assert result["charge_level"] == 85
    assert result["is_charging"] is True
    assert result["is_discharging"] is False
    assert result["battery_voltage"] == 3.7
