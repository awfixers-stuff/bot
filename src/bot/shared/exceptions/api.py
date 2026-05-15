"""External API-related exceptions."""

from .base import BotError

__all__ = [
    "BotAPIConnectionError",
    "BotAPIError",
    "BotAPIPermissionError",
    "BotAPIRequestError",
    "BotAPIResourceNotFoundError",
]


class BotAPIError(BotError):
    """Base exception for API-related errors."""


class BotAPIConnectionError(BotAPIError):
    """Raised when there's an issue connecting to an external API."""

    def __init__(self, service_name: str, original_error: Exception) -> None:
        self.service_name = service_name
        self.original_error = original_error
        super().__init__(f"Connection error with {service_name}: {original_error}")


class BotAPIRequestError(BotAPIError):
    """Raised when an API request fails with a specific status code."""

    def __init__(self, service_name: str, status_code: int, reason: str) -> None:
        self.service_name = service_name
        self.status_code = status_code
        self.reason = reason
        super().__init__(
            f"API request to {service_name} failed with status {status_code}: {reason}",
        )


class BotAPIResourceNotFoundError(BotAPIRequestError):
    """Raised when an API request results in a 404 or similar resource not found error."""

    def __init__(
        self,
        service_name: str,
        resource_identifier: str,
        status_code: int = 404,
    ) -> None:
        self.resource_identifier = resource_identifier
        super().__init__(
            service_name,
            status_code,
            reason=f"Resource '{resource_identifier}' not found.",
        )


class BotAPIPermissionError(BotAPIRequestError):
    """Raised when an API request fails due to permissions (e.g., 403 Forbidden)."""

    def __init__(self, service_name: str, status_code: int = 403) -> None:
        super().__init__(
            service_name,
            status_code,
            reason="API request failed due to insufficient permissions.",
        )
