"""Poll unban moderation command.

This module provides functionality to remove poll bans from Discord members.
It integrates with the moderation case tracking system.
"""

import discord
from discord.ext import commands

from bot.core.bot import Bot
from bot.core.checks import requires_command_permission
from bot.core.flags import PollUnbanFlags
from bot.database.models import CaseType as DBCaseType

from . import ModerationCogBase


class PollUnban(ModerationCogBase):
    """Discord cog for poll unban moderation commands.

    This cog provides the pollunban command which restores a member's
    ability to create polls in the server.
    """

    def __init__(self, bot: Bot) -> None:
        """Initialize the PollUnban cog.

        Parameters
        ----------
        bot : Bot
            The bot instance to attach this cog to.
        """
        super().__init__(bot)

    @commands.hybrid_command(
        name="pollunban",
        aliases=["pub"],
    )
    @commands.guild_only()
    @requires_command_permission()
    async def poll_unban(
        self,
        ctx: commands.Context[Bot],
        member: discord.Member,
        *,
        flags: PollUnbanFlags,
    ) -> None:
        """
        Remove a poll ban from a member.

        Parameters
        ----------
        ctx : commands.Context[Bot]
            The context object.
        member : discord.Member
            The member to remove poll ban from.
        flags : PollUnbanFlags
            The flags for the command. (reason: str, silent: bool)
        """
        assert ctx.guild

        # Check if user is poll banned
        if not await self.is_pollbanned(ctx.guild.id, member.id):
            if ctx.interaction:
                await ctx.interaction.followup.send(
                    "User is not poll banned.",
                    ephemeral=True,
                )
            else:
                await ctx.reply("User is not poll banned.", mention_author=False)
            return

        # Permission checks are handled by the @requires_command_permission() decorator
        # Additional validation will be handled by the ModerationCoordinator service

        # Execute poll unban with case creation and DM
        await self.moderate_user(
            ctx=ctx,
            case_type=DBCaseType.POLLUNBAN,
            user=member,
            reason=flags.reason,
            silent=flags.silent,
            dm_action="poll unbanned",
            actions=[],  # No Discord API actions needed for poll unban
        )


async def setup(bot: Bot) -> None:
    """Set up the PollUnban cog.

    Parameters
    ----------
    bot : Bot
        The bot instance to add the cog to.
    """
    await bot.add_cog(PollUnban(bot))
