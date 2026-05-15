"""
Guild controller for Bot Bot.

Provides database operations for the Guild model, including creation,
lookup, and guild-level aggregates.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from loguru import logger

from bot.database.controllers.base import BaseController
from bot.database.models import Guild

if TYPE_CHECKING:
    from bot.database.service import DatabaseService


class GuildController(BaseController[Guild]):
    """Controller for guild-level database operations."""

    def __init__(self, db: DatabaseService | None = None) -> None:
        """Initialize the guild controller.

        Parameters
        ----------
        db : DatabaseService | None, optional
            The database service instance.
        """
        super().__init__(Guild, db)

    async def get_or_create_guild(self, guild_id: int) -> Guild:
        """
        Get a guild by ID or create one if it doesn't exist.

        Parameters
        ----------
        guild_id : int
            The Discord guild ID.

        Returns
        -------
        Guild
            The guild record (existing or newly created).
        """
        guild, _ = await self.get_or_create(id=guild_id)
        return guild

    async def insert_guild_by_id(
        self,
        guild_id: int,
        **kwargs: Any,
    ) -> Guild:
        """
        Insert a new guild record by ID.

        Parameters
        ----------
        guild_id : int
            The Discord guild ID.
        **kwargs : Any
            Additional fields to set on the guild record.

        Returns
        -------
        Guild
            The newly created guild record.
        """
        return await self.create(id=guild_id, **kwargs)
