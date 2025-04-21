"""Remote helpers (HTTP polling, etc.)."""

from __future__ import annotations

import logging
from typing import Final

import requests
from requests.exceptions import RequestException
from typing_extensions import TypedDict


logger: Final = logging.getLogger(__name__)


class _FlagResponse(TypedDict, total=False):
    awake: bool


def should_stay_awake(url: str, timeout: float = 3.0) -> bool:
    """
    Query *url* (expected to return ``{"awake": true|false}``) and
    return **True** only when it explicitly says ``true``.

    Network errors, non-200 status, invalid JSON, or missing key
    all resolve to **False** (fail closed → sleep).
    """
    try:
        resp = requests.get(url, timeout=timeout)
        if resp.status_code != 200:
            logger.debug("stay-awake: HTTP %s from %s", resp.status_code, url)
            return False

        data: _FlagResponse = resp.json()  # type: ignore[assignment]
        return bool(data.get("awake", False))

    except (ValueError, RequestException) as exc:  # JSON parse / network error
        logger.debug("stay-awake: request failed (%s)", exc)
        return False
