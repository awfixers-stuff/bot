"""Bot-specific exception types.

This package defines only exception classes. For asyncio gather helpers:

- ``bot.shared.asyncio_gather.handle_gather_result`` — generic typing guard
- ``bot.database.gather_results.handle_case_result`` — when results are ``Case`` instances
"""

from .api import (
    BotAPIConnectionError,
    BotAPIError,
    BotAPIPermissionError,
    BotAPIRequestError,
    BotAPIResourceNotFoundError,
)
from .base import (
    BotConfigurationError,
    BotError,
    BotGracefulShutdown,
    BotRuntimeError,
    BotSetupError,
)
from .database import (
    BotDatabaseConnectionError,
    BotDatabaseError,
    BotDatabaseMigrationError,
    BotDatabaseQueryError,
)
from .execution import (
    BotCodeExecutionError,
    BotCompilationError,
    BotInvalidCodeFormatError,
    BotMissingCodeError,
    BotUnsupportedLanguageError,
)
from .permissions import (
    BotAppCommandPermissionLevelError,
    BotPermissionDeniedError,
    BotPermissionError,
    BotPermissionLevelError,
)
from .services import (
    BotCogLoadError,
    BotDependencyResolutionError,
    BotFileWatchError,
    BotHotReloadConfigurationError,
    BotHotReloadError,
    BotModuleReloadError,
    BotServiceError,
)

__all__ = [
    "BotAPIConnectionError",
    "BotAPIError",
    "BotAPIPermissionError",
    "BotAPIRequestError",
    "BotAPIResourceNotFoundError",
    "BotAppCommandPermissionLevelError",
    "BotCodeExecutionError",
    "BotCogLoadError",
    "BotCompilationError",
    "BotConfigurationError",
    "BotDatabaseConnectionError",
    "BotDatabaseError",
    "BotDatabaseMigrationError",
    "BotDatabaseQueryError",
    "BotDependencyResolutionError",
    "BotError",
    "BotFileWatchError",
    "BotGracefulShutdown",
    "BotHotReloadConfigurationError",
    "BotHotReloadError",
    "BotInvalidCodeFormatError",
    "BotMissingCodeError",
    "BotModuleReloadError",
    "BotPermissionDeniedError",
    "BotPermissionError",
    "BotPermissionLevelError",
    "BotRuntimeError",
    "BotServiceError",
    "BotSetupError",
    "BotUnsupportedLanguageError",
]
