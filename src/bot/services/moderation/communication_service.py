"""
Communication service for moderation operations.

Handles DM sending, embed creation, and user communication without
the complexity of mixin inheritance.
"""

import contextlib
from datetime import datetime

import discord
from discord.ext import commands
from loguru import logger

from bot.core.bot import Bot
from bot.shared.config import CONFIG
from bot.shared.constants import EMBED_COLORS


class CommunicationService:
    """
    Service for handling moderation-related communication.

    Manages DM sending, embed creation, and user notifications
    with proper error handling and timeouts.
    """

    def __init__(self, bot: Bot):
        """
        Initialize the communication service.

        Parameters
        ----------
        bot : Bot
            The Discord bot instance.
        """
        self.bot = bot

    async def send_dm(
        self,
        ctx: commands.Context[Bot],
        silent: bool,
        user: discord.Member | discord.User,
        reason: str,
        dm_action: str,
    ) -> bool:
        """
        Send a DM to a user about a moderation action.

        Parameters
        ----------
        ctx : commands.Context[Bot]
            Command context.
        silent : bool
            Whether to send DM (if False, returns False immediately).
        user : discord.Member | discord.User
            Target user.
        reason : str
            Reason for the action.
        dm_action : str
            Action description for DM.

        Returns
        -------
        bool
            True if DM was sent successfully, False otherwise.
        """
        if silent:
            logger.debug(f"Skipping DM to {user.id} (silent mode enabled)")
            return False

        try:
            embed = self._create_dm_embed(dm_action, reason, ctx.author)
            await user.send(embed=embed)
            logger.info(
                f"Moderation DM sent to {user} ({user.id}) - Action: {dm_action}",
            )
        except discord.Forbidden:
            logger.warning(
                f"Failed to DM {user} ({user.id}) - DMs disabled or bot blocked",
            )
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending DM to {user} ({user.id}): {e}")
            return False
        else:
            return True

    async def send_error_response(
        self,
        ctx: commands.Context[Bot] | discord.Interaction,
        message: str,
        ephemeral: bool = True,
    ) -> None:
        """
        Send an error response to the user.

        Parameters
        ----------
        ctx : commands.Context[Bot] | discord.Interaction
            Command context.
        message : str
            Error message to send.
        ephemeral : bool, optional
            Whether the response should be ephemeral, by default True.
        """
        try:
            if isinstance(ctx, discord.Interaction):
                if ctx.response.is_done():
                    await ctx.followup.send(message, ephemeral=ephemeral)
                else:
                    await ctx.response.send_message(message, ephemeral=ephemeral)
            else:
                # ctx is commands.Context[Bot] here
                await ctx.reply(message, mention_author=False)
            logger.debug(f"Error response sent: {message[:50]}...")
        except discord.HTTPException as e:
            logger.warning(
                f"Failed to send error response, retrying without reply: {e}",
            )
            # If sending fails, try to send without reply
            with contextlib.suppress(discord.HTTPException):
                if isinstance(ctx, discord.Interaction):
                    # For interactions, use followup
                    await ctx.followup.send(message, ephemeral=ephemeral)
                else:
                    # For command contexts, use send
                    await ctx.send(message)
                logger.debug("Error response sent successfully on retry")

    def create_embed(
        self,
        ctx: commands.Context[Bot],
        title: str,
        fields: list[tuple[str, str, bool]],
        color: int,
        icon_url: str,
        timestamp: datetime | None = None,
        thumbnail_url: str | None = None,
    ) -> discord.Embed:
        """
        Create a moderation embed.

        Parameters
        ----------
        ctx : commands.Context[Bot]
            Command context.
        title : str
            Embed title.
        fields : list[tuple[str, str, bool]]
            List of (name, value, inline) tuples.
        color : int
            Embed color.
        icon_url : str
            Icon URL for the embed.
        timestamp : datetime | None, optional
            Optional timestamp, by default None.
        thumbnail_url : str | None, optional
            Optional thumbnail URL, by default None.

        Returns
        -------
        discord.Embed
            The created embed.
        """
        embed = discord.Embed(
            title=title,
            color=color,
            timestamp=timestamp or discord.utils.utcnow(),
        )

        embed.set_author(name=ctx.author.name, icon_url=icon_url)

        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)

        if thumbnail_url:
            embed.set_thumbnail(url=thumbnail_url)

        embed.set_footer(
            text=f"Requested by {ctx.author}",
            icon_url=ctx.author.display_avatar.url,
        )

        return embed

    async def send_embed(
        self,
        ctx: commands.Context[Bot],
        embed: discord.Embed,
        log_type: str = "mod",
    ) -> discord.Message | None:
        """
        Send an embed and optionally log it.

        For slash commands (after defer), uses interaction.followup.send().
        For prefix commands, uses ctx.send().

        Parameters
        ----------
        ctx : commands.Context[Bot]
            Command context.
        embed : discord.Embed
            The embed to send.
        log_type : str, optional
            Type of log entry, by default "mod".

        Returns
        -------
        discord.Message | None
            The sent message if successful.
        """
        try:
            if ctx.interaction:
                # Slash command - use followup after defer
                message = await ctx.interaction.followup.send(
                    embed=embed,
                    ephemeral=True,
                    wait=True,  # Return the message object
                )
                logger.debug(
                    f"Ephemeral embed sent successfully for {log_type} log (slash)",
                )
            else:
                # Prefix command - use normal send
                message = await ctx.send(embed=embed, mention_author=False)
                logger.debug(f"Embed sent successfully for {log_type} log (prefix)")

        except discord.HTTPException as e:
            logger.error(f"Failed to send {log_type} embed: {e}")
            await self.send_error_response(ctx, "Failed to send embed")
            return None
        else:
            return message

    async def _get_guild_log_channels(
        self,
        guild_id: int,
    ) -> tuple[int | None, int | None]:
        """
        Get audit log and mod log channel IDs from static config.

        Parameters
        ----------
        guild_id : int
            The guild ID (unused, kept for backward compatibility).

        Returns
        -------
        tuple[int | None, int | None]
            Tuple of (audit_log_id, mod_log_id).
        """
        return CONFIG.LOG_CHANNELS.AUDIT_LOG_ID, CONFIG.LOG_CHANNELS.MOD_LOG_ID

    async def send_audit_log_embed(  # noqa: PLR0911
        self,
        ctx: commands.Context[Bot],
        embed: discord.Embed,
    ) -> discord.Message | None:
        """
        Send an embed to the audit log channel.

        Parameters
        ----------
        ctx : commands.Context[Bot]
            Command context.
        embed : discord.Embed
            The embed to send to audit log.

        Returns
        -------
        discord.Message | None
            The sent audit log message if successful, None otherwise.
        """
        if not ctx.guild:
            logger.warning("Cannot send audit log embed: no guild context")
            return None

        audit_log_id: int | None = None
        audit_channel: discord.TextChannel | None = None

        try:
            # Get audit log channel ID from guild config (with caching)
            audit_log_id, _ = await self._get_guild_log_channels(ctx.guild.id)
            if not audit_log_id:
                logger.debug(
                    f"No audit log channel configured for guild {ctx.guild.id}",
                )
                return None

            # Get the audit log channel
            channel = ctx.guild.get_channel(audit_log_id)
            if not channel:
                logger.warning(
                    f"Audit log channel {audit_log_id} not found in guild {ctx.guild.id}",
                )
                return None

            # Check if we can send messages to the channel
            if not isinstance(channel, discord.TextChannel):
                logger.warning(
                    f"Audit log channel {audit_log_id} is not a text channel",
                )
                return None

            audit_channel = channel
        except Exception as e:
            # Handle any unexpected errors during setup
            logger.error(f"Unexpected error during audit log setup: {e}")
            return None
        else:
            # Send the embed to audit log - only reached if no early returns occurred above
            try:
                audit_message = await audit_channel.send(embed=embed)
            except discord.Forbidden:
                logger.warning(
                    f"Missing permissions to send to audit log channel {audit_log_id or 'unknown'} in guild {ctx.guild.id}",
                )
                return None
            except discord.HTTPException as e:
                logger.error(
                    f"Failed to send audit log embed to channel {audit_log_id or 'unknown'}: {e}",
                )
                return None
            except Exception as e:
                logger.error(f"Unexpected error sending audit log embed: {e}")
                return None
            else:
                # Successfully sent the message
                logger.info(
                    f"Audit log embed sent to #{audit_channel.name} ({audit_channel.id}) in {ctx.guild.name}",
                )
                return audit_message

    async def send_mod_log_embed(  # noqa: PLR0911
        self,
        ctx: commands.Context[Bot],
        embed: discord.Embed,
    ) -> discord.Message | None:
        """
        Send an embed to the mod log channel.

        Parameters
        ----------
        ctx : commands.Context[Bot]
            Command context.
        embed : discord.Embed
            The embed to send to mod log.

        Returns
        -------
        discord.Message | None
            The sent mod log message if successful, None otherwise.
        """
        if not ctx.guild:
            logger.warning("Cannot send mod log embed: no guild context")
            return None

        mod_log_id: int | None = None
        mod_channel: discord.TextChannel | None = None

        try:
            # Get mod log channel ID from guild config (with caching)
            _, mod_log_id = await self._get_guild_log_channels(ctx.guild.id)
            if not mod_log_id:
                logger.debug(f"No mod log channel configured for guild {ctx.guild.id}")
                return None

            # Get the mod log channel
            channel = ctx.guild.get_channel(mod_log_id)
            if not channel:
                logger.warning(
                    f"Mod log channel {mod_log_id} not found in guild {ctx.guild.id}",
                )
                return None

            # Check if we can send messages to the channel
            if not isinstance(channel, discord.TextChannel):
                logger.warning(f"Mod log channel {mod_log_id} is not a text channel")
                return None

            mod_channel = channel
        except Exception as e:
            # Handle any unexpected errors during setup
            logger.error(f"Unexpected error during mod log setup: {e}")
            return None
        else:
            # Send the embed to mod log - only reached if no early returns occurred above
            try:
                mod_message = await mod_channel.send(embed=embed)
            except discord.Forbidden:
                logger.warning(
                    f"Missing permissions to send to mod log channel {mod_log_id or 'unknown'} in guild {ctx.guild.id}",
                )
                return None
            except discord.HTTPException as e:
                logger.error(
                    f"Failed to send mod log embed to channel {mod_log_id or 'unknown'}: {e}",
                )
                return None
            except Exception as e:
                logger.error(f"Unexpected error sending mod log embed: {e}")
                return None
            else:
                # Successfully sent the message
                logger.info(
                    f"Mod log embed sent to #{mod_channel.name} ({mod_channel.id}) in {ctx.guild.name}",
                )
                return mod_message

    def _create_dm_embed(
        self,
        action: str,
        reason: str,
        moderator: discord.User | discord.Member,
    ) -> discord.Embed:
        """
        Create a DM embed for moderation actions.

        Parameters
        ----------
        action : str
            The action that was taken.
        reason : str
            Reason for the action.
        moderator : discord.User
            The moderator who performed the action.

        Returns
        -------
        discord.Embed
            The DM embed.
        """
        embed = discord.Embed(
            title=f"You have been {action}",
            color=EMBED_COLORS["CASE"],
            timestamp=discord.utils.utcnow(),
        )

        embed.add_field(
            name="Reason",
            value=reason or "No reason provided",
            inline=False,
        )

        embed.add_field(
            name="Moderator",
            value=f"{moderator} ({moderator.id})",
            inline=False,
        )

        embed.set_footer(
            text="If you believe this was an error, please contact server staff",
        )

        return embed
