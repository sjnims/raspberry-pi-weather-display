"""Exception classes for weather API interactions.

This module defines a hierarchy of exception classes for handling
various error conditions when interacting with weather APIs.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


class WeatherAPIError(Exception):
    """Error during OpenWeather API request or response parsing.

    Raised when the API request fails due to network issues,
    invalid API key, rate limiting, or malformed response data.
    Includes the underlying exception and response details
    when available.
    """

    def __init__(
        self, code: int, message: str, response: Optional[Dict[str, Any]] = None
    ) -> None:
        """Initialize the exception.

        Args:
            code: HTTP status code or custom error code
            message: Human-readable error message
            response: Optional raw API response for debugging
        """
        super().__init__(f"[{code}] {message}")
        self.code: int = code
        self.message: str = message
        self.response: Optional[Dict[str, Any]] = response

    @property
    def is_client_error(self) -> bool:
        """Check if this is a client-side error (4xx).

        Returns:
            True for 400-499 status codes
        """
        return 400 <= self.code < 500

    @property
    def is_server_error(self) -> bool:
        """Check if this is a server-side error (5xx).

        Returns:
            True for 500-599 status codes
        """
        return self.code >= 500

    @classmethod
    def from_response(
        cls, response: Dict[str, Any], status_code: int = 0
    ) -> WeatherAPIError:
        """Create an error from an API response.

        Args:
            response: API response dictionary
            status_code: HTTP status code

        Returns:
            Appropriate WeatherAPIError subclass
        """
        if 400 <= status_code < 500:
            if status_code == 401 or status_code == 403:
                return AuthenticationError(
                    status_code, response.get("message", "Authentication failed")
                )
            elif status_code == 404:
                return NotFoundError(
                    status_code, response.get("message", "Resource not found")
                )
            elif status_code == 429:
                return RateLimitError(
                    status_code, response.get("message", "Rate limit exceeded")
                )
            return ClientError(
                status_code, response.get("message", "Client error"), response
            )
        elif status_code >= 500:
            return ServerError(
                status_code, response.get("message", "Server error"), response
            )

        # Default case
        return cls(status_code, response.get("message", "Unknown error"), response)


class NetworkError(WeatherAPIError):
    """Raised when a network issue prevents API communication."""

    def __init__(
        self, message: str, original_error: Optional[Exception] = None
    ) -> None:
        """Initialize with network error details.

        Args:
            message: Description of the network error
            original_error: The original exception that was caught
        """
        super().__init__(0, message)
        self.original_error = original_error


class AuthenticationError(WeatherAPIError):
    """Raised when API authentication fails (invalid API key)."""

    pass


class NotFoundError(WeatherAPIError):
    """Raised when a requested resource doesn't exist."""

    pass


class RateLimitError(WeatherAPIError):
    """Raised when rate limits are exceeded."""

    pass


class ClientError(WeatherAPIError):
    """Raised for general 4xx client errors."""

    pass


class ServerError(WeatherAPIError):
    """Raised for 5xx server errors."""

    pass


class ParseError(WeatherAPIError):
    """Raised when API response parsing fails."""

    def __init__(
        self, message: str, original_error: Optional[Exception] = None
    ) -> None:
        """Initialize with parsing error details.

        Args:
            message: Description of the parsing error
            original_error: The original exception that was caught
        """
        super().__init__(0, message)
        self.original_error = original_error
