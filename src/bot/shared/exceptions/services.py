"""Service, cog loading, and hot-reload exceptions."""

from .base import BotError

__all__ = [
    "BotCogLoadError",
    "BotDependencyResolutionError",
    "BotFileWatchError",
    "BotHotReloadConfigurationError",
    "BotHotReloadError",
    "BotModuleReloadError",
    "BotServiceError",
]


class BotServiceError(BotError):
    """Base exception for service-related errors."""


class BotCogLoadError(BotServiceError):
    """Raised when a cog fails to load."""


class BotHotReloadError(BotServiceError):
    """Base exception for hot reload errors."""


class BotDependencyResolutionError(BotHotReloadError):
    """Raised when dependency resolution fails."""


class BotFileWatchError(BotHotReloadError):
    """Raised when file watching fails."""


class BotModuleReloadError(BotHotReloadError):
    """Raised when module reloading fails."""


class BotHotReloadConfigurationError(BotHotReloadError):
    """Raised when hot reload configuration is invalid."""
