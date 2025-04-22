"""Tests for rpiweather.power helpers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from pathlib import Path
from typing import cast
import builtins

import pytest
from rpiweather import power


class _FakeSubprocess:
    """Capture arguments to subprocess.run."""

    def __init__(self) -> None:
        self.called: Dict[str, Any] = {}

    def run(self, cmd: list[str], **kwargs: Any) -> None:  # noqa: D401
        self.called["cmd"] = cmd
        self.called["kwargs"] = kwargs


def test_graceful_shutdown(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeSubprocess()
    monkeypatch.setattr(power, "subprocess", fake, raising=False)

    power.graceful_shutdown()

    assert fake.called["cmd"] == ["sudo", "shutdown", "-h", "now"]
    assert fake.called["kwargs"]["check"] is True  # type: ignore[index]


def test_schedule_wakeup_pijuice(monkeypatch: pytest.MonkeyPatch) -> None:
    # Force PiJuice path to succeed
    called: dict[str, Any] = {}

    def fake_set_alarm(_dt: datetime) -> bool:  # noqa: D401
        called["ok"] = True
        return True

    monkeypatch.setattr(power, "_set_pijuice_alarm", fake_set_alarm, raising=True)

    power.schedule_wakeup(datetime.now(timezone.utc) + timedelta(minutes=10))
    assert called.get("ok") is True


def test_schedule_wakeup_rtc(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """PiJuice fails → fallback writes to fake wakealarm."""

    def fake_set_alarm(_dt: datetime) -> bool:  # noqa: D401
        return False

    wake_file: Path = tmp_path / "wakealarm"
    wake_file.write_text("")  # create

    # patch alarm & open()
    monkeypatch.setattr(power, "_set_pijuice_alarm", fake_set_alarm, raising=True)

    # Provide replacement that calls original built‑ins open to avoid recursion
    orig_open = builtins.open  # save

    def fake_open(*_args: Any, **_kwargs: Any):  # noqa: D401
        return orig_open(wake_file, "w", encoding="utf-8")

    monkeypatch.setattr(builtins, "open", cast(Any, fake_open), raising=True)

    power.schedule_wakeup(datetime.now(timezone.utc) + timedelta(minutes=10))
    assert wake_file.read_text().strip() != ""
