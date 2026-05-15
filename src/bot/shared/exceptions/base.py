"""Root and cross-cutting configuration/runtime exceptions."""

__all__ = [
    "BotConfigurationError",
    "BotError",
    "BotGracefulShutdown",
    "BotRuntimeError",
    "BotSetupError",
]


class BotError(Exception):
    """Base exception for all Bot-specific errors."""


class BotConfigurationError(BotError):
    """Raised when there's a configuration issue."""


class BotRuntimeError(BotError):
    """Raised when there's a runtime issue."""


class BotSetupError(BotError):
    """Raised when bot setup fails."""


class BotGracefulShutdown(BotError):  # noqa: N818
    """Raised when bot shuts down gracefully."""
