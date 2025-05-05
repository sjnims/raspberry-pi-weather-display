"""Unit tests for rpiweather.remote.should_stay_awake."""

from __future__ import annotations

from typing import Any

import pytest
import requests

from rpiweather.remote import create_wake_state_provider


class _MockResponse:
    """Minimal requests.Response shim for testing."""

    def __init__(
        self,
        status_code: int,
        payload: dict[str, Any] | None = None,
        *,  # keyword-only
        bad_json: bool = False,
    ) -> None:
        self.status_code = status_code
        self._payload = payload or {}
        self._bad_json = bad_json

    # requests.Response.json()
    def json(self) -> dict[str, Any]:
        if self._bad_json:
            raise ValueError("Invalid JSON")
        return self._payload


# ---------------------------------------------------------------------------


def test_awake_true(monkeypatch: pytest.MonkeyPatch) -> None:
    def mock_get(*_a: Any, **_kw: Any):
        return _MockResponse(200, {"awake": True})

    monkeypatch.setattr(
        "rpiweather.remote.requests.get",
        mock_get,
        raising=True,
    )
    assert create_wake_state_provider("http://dummy").should_stay_awake() is True


def test_awake_false(monkeypatch: pytest.MonkeyPatch) -> None:
    def mock_get(*_a: Any, **_kw: Any):
        return _MockResponse(200, {"awake": False})

    monkeypatch.setattr("rpiweather.remote.requests.get", mock_get, raising=True)
    assert create_wake_state_provider("http://dummy").should_stay_awake() is False


@pytest.mark.parametrize(
    "resp",
    [
        _MockResponse(404, {}),  # HTTP error
        _MockResponse(200, bad_json=True),  # JSON parse error
    ],
)
def test_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
    resp: _MockResponse,
) -> None:
    def mock_get(*_a: Any, **_kw: Any):
        return resp

    monkeypatch.setattr("rpiweather.remote.requests.get", mock_get, raising=True)
    assert create_wake_state_provider("http://dummy").should_stay_awake() is False


def test_network_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def mock_get(*_a: Any, **_kw: Any) -> None:
        raise requests.exceptions.Timeout("network down")

    monkeypatch.setattr("rpiweather.remote.requests.get", mock_get, raising=True)
    assert create_wake_state_provider("http://dummy").should_stay_awake() is False
