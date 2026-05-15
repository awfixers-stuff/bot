"""Event handlers for Bot Bot such as on ready, on guild join, on guild remove, on member join (level role restore), on message and on guild channel create."""

import discord
from discord.ext import commands
from loguru import logger

from bot.core.base_cog import BaseCog
from bot.core.bot import Bot
from bot.core.permission_system import get_permission_system
from bot.modules.features.levels import (
    LEVEL_XP_LEVEL_MISMATCH_RECONCILE_THRESHOLD,
    LevelsService,
)
from bot.shared.config import CONFIG


class EventHandler(BaseCog):
    """Event handlers for on_ready, guild join/remove, member join (level role restore), on_message, and guild channel create."""

    def __init__(self, bot: Bot) -> None:
        """
        Initialize the EventHandler cog.

        Parameters
        ----------
        bot : Bot
            The bot instance.
        """
        super().__init__(bot)
        self._guilds_registered = False

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """Handle bot ready event."""
        try:
            if not self.bot.setup_complete:
                logger.warning("on_ready fired before setup_complete")
                if not self.bot.first_ready:
                    self.bot.first_ready = True
                self.bot.guilds_registered.set()
                return

            self.bot.guilds_registered.clear()
            logger.info("Bot ready (single-guild mode)")

            # Mark first ready
            if not self.bot.first_ready:
                self.bot.first_ready = True
                logger.debug("First on_ready event completed")

                # Pre-warm permission caches to avoid cold-start delays on first commands
                try:
                    permission_system = get_permission_system()
                    await permission_system.prewarm_cache_for_all_guilds()
                except Exception as e:
                    logger.warning(f"Failed to pre-warm permission caches: {e}")

            self._guilds_registered = True
            self.bot.guilds_registered.set()
        except Exception:
            if not self.bot.first_ready:
                self.bot.first_ready = True
            self.bot.guilds_registered.set()
            logger.exception("EventHandler.on_ready failed (cog=EventHandler)")
            raise

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild) -> None:
        """On guild join event handler."""
        logger.info(f"Guild joined: {guild.id} ({guild.name})")

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        """Re-apply XP level roles when a member rejoins with existing level data."""
        if member.bot:
            return

        levels_cog = self.bot.get_cog("LevelsService")
        if not isinstance(levels_cog, LevelsService):
            return

        if await self.bot.is_jailed(member.guild.id, member.id):
            return

        level_data = await self.db.levels.get_user_level_data(
            member.id,
            member.guild.id,
        )
        if level_data is None or level_data.blacklisted:
            return

        current_level = level_data.level
        expected_from_xp = levels_cog.calculate_level(level_data.xp)
        if (
            abs(expected_from_xp - current_level)
            > LEVEL_XP_LEVEL_MISMATCH_RECONCILE_THRESHOLD
        ):
            effective_level = expected_from_xp
        else:
            effective_level = current_level

        if effective_level <= 0:
            return

        try:
            await levels_cog.update_roles(member, member.guild, effective_level)
        except discord.DiscordException as e:
            logger.warning(
                "Failed to restore level roles for member {} in guild {} ({}): {}",
                member.id,
                member.guild.id,
                type(e).__name__,
                e,
            )
        except Exception:
            logger.exception(
                "Unexpected error restoring level roles for member {} in guild {}",
                member.id,
                member.guild.id,
            )
        else:
            logger.debug(
                "Restored level roles for {} ({}) at effective level {} in guild {}",
                member.name,
                member.id,
                effective_level,
                member.guild.id,
            )

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild) -> None:
        """On guild remove event handler."""
        logger.info(f"Bot removed from guild: {guild.name} ({guild.id})")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """On message event handler."""
        try:
            # Skip event processing during maintenance mode (except IRC bridge)
            if getattr(self.bot, "maintenance_mode", False):
                # Still allow IRC bridge during maintenance
                if message.webhook_id in CONFIG.IRC_CONFIG.BRIDGE_WEBHOOK_IDS and (
                    message.content.startswith(f"{CONFIG.get_prefix()}s ")
                    or message.content.startswith(f"{CONFIG.get_prefix()}snippet ")
                ):
                    ctx = await self.bot.get_context(message)
                    await self.bot.invoke(ctx)
                return

            # Allow the IRC bridge to use the snippet command only
            if message.webhook_id in CONFIG.IRC_CONFIG.BRIDGE_WEBHOOK_IDS and (
                message.content.startswith(f"{CONFIG.get_prefix()}s ")
                or message.content.startswith(f"{CONFIG.get_prefix()}snippet ")
            ):
                ctx = await self.bot.get_context(message)
                await self.bot.invoke(ctx)
        except Exception as e:
            logger.exception(
                f"Error in event handler on_message listener for message {message.id}: {e}",
            )

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel) -> None:
        """Automatically deny view permissions for jail role on new channels."""
        if not channel.guild:
            return

        # Get jail role from static config
        jail_role_id = CONFIG.LOG_CHANNELS.JAIL_ROLE_ID
        if not jail_role_id:
            logger.debug(
                f"No jail role configured for guild {channel.guild.id}, skipping channel setup",
            )
            return

        jail_role = channel.guild.get_role(jail_role_id)
        if not jail_role:
            logger.warning(
                f"Jail role {jail_role_id} not found in guild {channel.guild.id}",
            )
            return

        # Set permissions to deny view for jail role
        try:
            await channel.set_permissions(
                jail_role,
                view_channel=False,
                read_messages=False,
                send_messages=False,
                reason="Auto-deny jail role on new channel",
            )
            logger.info(
                f"Blocked jail role from new channel: {channel.name} in {channel.guild.name}",
            )
        except discord.Forbidden:
            logger.warning(
                f"Missing permissions to set jail role permissions in {channel.name}",
            )
        except Exception as e:
            logger.error(f"Failed to set jail role permissions on {channel.name}: {e}")


async def setup(bot: Bot) -> None:
    """Cog setup for event handler.

    Parameters
    ----------
    bot : Bot
        The bot instance.
    """
    await bot.add_cog(EventHandler(bot))
