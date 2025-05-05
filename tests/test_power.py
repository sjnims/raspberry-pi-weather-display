"""Tests for rpiweather.power helpers."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from rpiweather import power
from rpiweather.power import LinuxRTCWakeup, PiJuiceWakeup, PowerManager


class _FakeSubprocess:
    """Capture arguments to subprocess.run."""

    def __init__(self) -> None:
        self.called: dict[str, Any] = {}

    def run(self, cmd: list[str], **kwargs: Any) -> None:
        self.called["cmd"] = cmd
        self.called["kwargs"] = kwargs


def test_graceful_shutdown(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeSubprocess()
    monkeypatch.setattr(power, "subprocess", fake, raising=False)

    PowerManager().shutdown()

    assert fake.called["cmd"] == ["sudo", "shutdown", "-h", "now"]
    assert fake.called["kwargs"]["check"] is True


def test_schedule_wakeup_pijuice(monkeypatch: pytest.MonkeyPatch) -> None:
    # Create a mock PiJuiceWakeup
    called: dict[str, bool] = {}

    class MockPiJuiceWakeup(PiJuiceWakeup):
        def set_wakeup(self, wake_time: datetime) -> bool:
            called["ok"] = True
            return True

    # Use only our mock provider
    power_manager = PowerManager(wakeup_providers=[MockPiJuiceWakeup()])

    # Test wakeup scheduling
    wake_time = datetime.now()
    result = power_manager.schedule_wakeup(wake_time)

    assert result is True
    assert called.get("ok") is True


def test_schedule_wakeup_rtc(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """PiJuice fails → fallback to system RTC."""

    # Mock PiJuice that fails
    class MockPiJuiceFail(PiJuiceWakeup):
        def set_wakeup(self, wake_time: datetime) -> bool:
            return False

    # Mock RTC with test file
    wake_file: Path = tmp_path / "wakealarm"
    wake_file.write_text("")  # create empty file

    class MockRTC(LinuxRTCWakeup):
        def __init__(self) -> None:
            super().__init__(str(wake_file))

    # Create manager with both providers
    power_manager = PowerManager(wakeup_providers=[MockPiJuiceFail(), MockRTC()])

    # Test wakeup scheduling
    wake_time = datetime.now()
    result = power_manager.schedule_wakeup(wake_time)

    assert result is True
    assert wake_file.read_text() != ""  # File should have been written to
