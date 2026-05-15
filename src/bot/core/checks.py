"""Dynamic permission system with database-driven command access control.

This module provides permission decorators and system initialization functions
for enforcing command-level permissions based on database configuration. All
permission requirements are stored in the database and evaluated per-guild at
runtime. Commands are denied by default if no explicit permission is configured.

The permission system is initialized during bot setup and provides decorators
for command access control. Guild administrators configure permissions through
the bot's configuration commands.
"""

# Dynamic permission decorator
from bot.core.decorators import requires_command_permission

# Core permission system functions
from bot.core.permission_system import (
    get_permission_system,
    init_permission_system,
)

# Permission exceptions
from bot.shared.exceptions import BotPermissionDeniedError

__all__ = [
    # Exceptions
    "BotPermissionDeniedError",
    # Core functions
    "get_permission_system",
    "init_permission_system",
    # The ONLY decorator - 100% dynamic
    "requires_command_permission",
]
