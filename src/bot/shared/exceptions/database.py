"""Database-related exceptions."""

from .base import BotError

__all__ = [
    "BotDatabaseConnectionError",
    "BotDatabaseError",
    "BotDatabaseMigrationError",
    "BotDatabaseQueryError",
]


class BotDatabaseError(BotError):
    """Base exception for database-related errors."""


class BotDatabaseConnectionError(BotDatabaseError):
    """Raised when database connection fails."""

    def __init__(
        self,
        message: str = "Database connection failed",
        original_error: Exception | None = None,
    ) -> None:
        self.original_error = original_error
        super().__init__(message)


class BotDatabaseMigrationError(BotDatabaseError):
    """Raised when database migration fails."""


class BotDatabaseQueryError(BotDatabaseError):
    """Raised when a database query fails."""
