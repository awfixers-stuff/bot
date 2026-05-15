"""Core module for Bot bot.

This module provides the core infrastructure including:
- Main bot class (Bot)
- Base cog class for extensions
- Command prefix resolution
- Permission system and decorators
- Common converters and utilities
"""

from bot.core.app import BotApp, get_prefix
from bot.core.base_cog import BaseCog
from bot.core.bot import Bot
from bot.core.checks import requires_command_permission
from bot.core.converters import get_channel_safe
from bot.core.permission_system import DEFAULT_RANKS, get_permission_system

__all__ = [
    # Core classes
    "BaseCog",
    "DEFAULT_RANKS",
    "Bot",
    "BotApp",
    # Functions
    "get_channel_safe",
    "get_permission_system",
    "get_prefix",
    "requires_command_permission",
]
