"""
Ban moderation command for Bot Bot.

This module provides the ban command functionality, allowing server
moderators to ban users from the server with various options.
"""

import discord
from discord.ext import commands

from bot.core.bot import Bot
from bot.core.checks import requires_command_permission
from bot.core.flags import BanFlags
from bot.database.models import CaseType as DBCaseType

from . import ModerationCogBase


class Ban(ModerationCogBase):
    """Ban command cog for moderating server members."""

    def __init__(self, bot: Bot) -> None:
        """Initialize the Ban cog.

        Parameters
        ----------
        bot : Bot
            The bot instance to initialize the cog with.
        """
        super().__init__(bot)

    @commands.hybrid_command(name="ban", aliases=["b"])
    @commands.guild_only()
    @requires_command_permission()
    async def ban(
        self,
        ctx: commands.Context[Bot],
        member: discord.Member | discord.User,
        *,
        flags: BanFlags,
    ) -> None:
        """
        Ban a member from the server.

        Parameters
        ----------
        ctx : commands.Context[Bot]
            The context in which the command is being invoked.
        member : discord.Member | discord.User
            The member to ban.
        flags : BanFlags
            The flags for the command. (reason: str, purge: int (< 7), silent: bool)
        """
        assert ctx.guild

        # Execute ban with case creation and DM
        await self.moderate_user(
            ctx=ctx,
            case_type=DBCaseType.BAN,
            user=member,
            reason=flags.reason,
            silent=flags.silent,
            dm_action="banned",
            actions=[
                (
                    lambda: (
                        ctx.guild.ban(
                            member,
                            reason=flags.reason,
                            delete_message_seconds=flags.purge * 86400,
                        )
                        if ctx.guild
                        else None
                    ),
                    type(None),
                ),
            ],
        )


async def setup(bot: Bot) -> None:
    """Set up the Ban cog.

    Parameters
    ----------
    bot : Bot
        The bot instance to add the cog to.
    """
    await bot.add_cog(Ban(bot))
