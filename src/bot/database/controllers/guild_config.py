"""
Guild configuration controller for Bot Bot.

Provides database operations for the GuildConfig model, including
CRUD, cache invalidation, and convenience accessors for common
guild configuration fields.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from loguru import logger

from bot.cache import GuildConfigCacheManager
from bot.database.controllers.base import BaseController
from bot.database.models import GuildConfig

if TYPE_CHECKING:
    from bot.database.service import DatabaseService


class GuildConfigController(BaseController[GuildConfig]):
    """Controller for guild configuration operations."""

    def __init__(self, db: DatabaseService | None = None) -> None:
        """Initialize the guild config controller.

        Parameters
        ----------
        db : DatabaseService | None, optional
            The database service instance.
        """
        super().__init__(GuildConfig, db)

    async def get_config_by_guild_id(self, guild_id: int) -> GuildConfig | None:
        """Get guild configuration by guild ID.

        Parameters
        ----------
        guild_id : int
            The Discord guild ID.

        Returns
        -------
        GuildConfig | None
            The guild configuration if found, None otherwise.
        """
        return await self.get_by_id(guild_id)

    async def get_or_create_config(
        self,
        guild_id: int,
        **defaults: Any,
    ) -> GuildConfig:
        """Get guild configuration, or create it with defaults if it doesn't exist.

        Parameters
        ----------
        guild_id : int
            The Discord guild ID.
        **defaults : Any
            Default values to use if creating a new config.

        Returns
        -------
        GuildConfig
            The guild configuration (existing or newly created).
        """
        config, _ = await self.get_or_create(defaults=defaults, id=guild_id)
        return config

    async def update_config(
        self,
        guild_id: int,
        **updates: Any,
    ) -> GuildConfig | None:
        """Update guild configuration.

        Automatically invalidates the guild config cache on changes.

        Parameters
        ----------
        guild_id : int
            The Discord guild ID.
        **updates : Any
            Fields to update.

        Returns
        -------
        GuildConfig | None
            The updated configuration, or None if not found.
        """
        result = await self.update_by_id(guild_id, **updates)

        if result and any(
            field in updates
            for field in (
                "audit_log_id",
                "mod_log_id",
                "join_log_id",
                "private_log_id",
                "report_log_id",
                "dev_log_id",
                "jail_role_id",
                "jail_channel_id",
            )
        ):
            await GuildConfigCacheManager().invalidate(guild_id)

        return result

    async def get_log_channel_ids(
        self,
        guild_id: int,
    ) -> tuple[int | None, int | None]:
        """Get audit log and mod log channel IDs for a guild.

        Parameters
        ----------
        guild_id : int
            The Discord guild ID.

        Returns
        -------
        tuple[int | None, int | None]
            Tuple of (audit_log_id, mod_log_id).
        """
        config = await self.get_by_id(guild_id)
        if config is None:
            return None, None
        return config.audit_log_id, config.mod_log_id

    async def get_jail_role_id(self, guild_id: int) -> int | None:
        """Get the jail role ID for a guild.

        Parameters
        ----------
        guild_id : int
            The Discord guild ID.

        Returns
        -------
        int | None
            The jail role ID, or None if not configured.
        """
        config = await self.get_by_id(guild_id)
        return config.jail_role_id if config else None

    async def get_jail_channel_id(self, guild_id: int) -> int | None:
        """Get the jail channel ID for a guild.

        Parameters
        ----------
        guild_id : int
            The Discord guild ID.

        Returns
        -------
        int | None
            The jail channel ID, or None if not configured.
        """
        config = await self.get_by_id(guild_id)
        return config.jail_channel_id if config else None

    async def get_jail_config(
        self,
        guild_id: int,
    ) -> tuple[int | None, int | None]:
        """Get both jail role and channel IDs for a guild.

        Parameters
        ----------
        guild_id : int
            The Discord guild ID.

        Returns
        -------
        tuple[int | None, int | None]
            Tuple of (jail_role_id, jail_channel_id).
        """
        config = await self.get_by_id(guild_id)
        if config is None:
            return None, None
        return config.jail_role_id, config.jail_channel_id

    async def update_jail_role_id(
        self,
        guild_id: int,
        role_id: int | None,
    ) -> GuildConfig | None:
        """Update the jail role ID for a guild.

        Parameters
        ----------
        guild_id : int
            The Discord guild ID.
        role_id : int | None
            The new jail role ID.

        Returns
        -------
        GuildConfig | None
            The updated configuration, or None if not found.
        """
        return await self.update_config(guild_id, jail_role_id=role_id)

    async def update_onboarding_stage(
        self,
        guild_id: int,
        stage: str,
    ) -> GuildConfig | None:
        """Update the onboarding stage for a guild.

        Parameters
        ----------
        guild_id : int
            The Discord guild ID.
        stage : str
            The onboarding stage value.

        Returns
        -------
        GuildConfig | None
            The updated configuration, or None if not found.
        """
        return await self.update_by_id(
            guild_id,
            onboarding_stage=stage,
            onboarding_completed=(stage == "completed"),
        )
