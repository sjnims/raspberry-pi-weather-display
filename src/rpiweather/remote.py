"""Remote helpers for system wake/sleep management."""

from __future__ import annotations

import logging
from typing import Final, Protocol, runtime_checkable
import urllib.parse

import requests
from requests.exceptions import RequestException
from typing_extensions import TypedDict


logger: Final = logging.getLogger(__name__)


class AwakeResponse(TypedDict, total=False):
    """Response structure for awake status endpoints."""

    awake: bool


@runtime_checkable
class WakeStateProvider(Protocol):
    """Protocol for determining if system should stay awake."""

    def should_stay_awake(self) -> bool:
        """Determine if the system should stay awake.

        Returns:
            True if the system should stay awake, False otherwise
        """
        ...


class HttpWakeStateProvider:
    """Implementation that checks an HTTP endpoint for wake state."""

    def __init__(self, url: str, timeout: float = 3.0) -> None:
        """Initialize with URL to check.

        Args:
            url: URL to query for wake state
            timeout: Timeout for HTTP request in seconds
        """
        # Validate URL
        parsed = urllib.parse.urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError(f"Invalid URL: {url}")

        self.url = url
        self.timeout = timeout

    def should_stay_awake(self) -> bool:
        """Check if system should stay awake based on HTTP response.

        Returns:
            True only if endpoint explicitly returns {"awake": true}
        """
        try:
            resp = requests.get(self.url, timeout=self.timeout)
            if resp.status_code != 200:
                logger.debug("stay-awake: HTTP %s from %s", resp.status_code, self.url)
                return False

            data: AwakeResponse = resp.json()  # type: ignore[assignment]
            return bool(data.get("awake", False))

        except (ValueError, RequestException) as exc:  # JSON parse / network error
            logger.debug("stay-awake: request failed (%s)", exc)
            return False


class AlwaysAwakeProvider:
    """Provider that always indicates system should stay awake."""

    def should_stay_awake(self) -> bool:
        """Always return True.

        Returns:
            Always True
        """
        return True


# Factory function to create appropriate provider
def create_wake_state_provider(url: str = "") -> WakeStateProvider:
    """Create a wake state provider based on configuration.

    Args:
        url: URL to check for wake state (empty means always awake)

    Returns:
        A WakeStateProvider implementation
    """
    if not url:
        return AlwaysAwakeProvider()
    return HttpWakeStateProvider(url)


# Legacy function for backward compatibility
def should_stay_awake(url: str, timeout: float = 3.0) -> bool:
    """Legacy function to maintain backward compatibility.

    Args:
        url: URL to query for wake state
        timeout: Timeout for HTTP request in seconds

    Returns:
        True only if endpoint explicitly returns {"awake": true}
    """
    provider = HttpWakeStateProvider(url, timeout)
    return provider.should_stay_awake()
