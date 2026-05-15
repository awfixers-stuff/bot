"""
User warning commands for Discord moderation.

This module provides functionality to issue warnings to Discord server members,
with automatic case tracking and notification systems.
"""

import discord
from discord.ext import commands

from bot.core.bot import Bot
from bot.core.checks import requires_command_permission
from bot.core.flags import WarnFlags
from bot.database.models import CaseType as DBCaseType

from . import ModerationCogBase


class Warn(ModerationCogBase):
    """Discord cog for issuing warnings to server members."""

    def __init__(self, bot: Bot) -> None:
        """Initialize the Warn cog.

        Parameters
        ----------
        bot : Bot
            The bot instance to attach this cog to.
        """
        super().__init__(bot)

    @commands.hybrid_command(
        name="warn",
        aliases=["w"],
    )
    @commands.guild_only()
    @requires_command_permission()
    async def warn(
        self,
        ctx: commands.Context[Bot],
        member: discord.Member,
        *,
        flags: WarnFlags,
    ) -> None:
        """
        Warn a member from the server.

        Parameters
        ----------
        ctx : commands.Context[Bot]
            The context in which the command is being invoked.
        member : discord.Member
            The member to warn.
        flags : WarnFlags
            The flags for the command. (reason: str, silent: bool)
        """
        assert ctx.guild

        # Execute warn with case creation and DM
        await self.moderate_user(
            ctx=ctx,
            case_type=DBCaseType.WARN,
            user=member,
            reason=flags.reason,
            silent=flags.silent,
            dm_action="warned",
            actions=[],  # No Discord API actions needed for warnings
        )


async def setup(bot: Bot) -> None:
    """Set up the Warn cog.

    Parameters
    ----------
    bot : Bot
        The bot instance to add the cog to.
    """
    await bot.add_cog(Warn(bot))
