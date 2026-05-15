"""Snippet unban moderation command.

This module provides functionality to remove snippet bans from Discord members.
It integrates with the moderation case tracking system.
"""

import discord
from discord.ext import commands

from bot.core.bot import Bot
from bot.core.checks import requires_command_permission
from bot.core.flags import SnippetUnbanFlags
from bot.database.models import CaseType

from . import ModerationCogBase


class SnippetUnban(ModerationCogBase):
    """Discord cog for snippet unban moderation commands.

    This cog provides the snippetunban command which restores a member's
    ability to create snippets in the server.
    """

    def __init__(self, bot: Bot) -> None:
        """Initialize the SnippetUnban cog.

        Parameters
        ----------
        bot : Bot
            The bot instance to attach this cog to.
        """
        super().__init__(bot)

    @commands.hybrid_command(
        name="snippetunban",
        aliases=["sub"],
    )
    @commands.guild_only()
    @requires_command_permission()
    async def snippet_unban(
        self,
        ctx: commands.Context[Bot],
        member: discord.Member,
        *,
        flags: SnippetUnbanFlags,
    ) -> None:
        """
        Remove a snippet ban from a member.

        Parameters
        ----------
        ctx : commands.Context[Bot]
            The context object.
        member : discord.Member
            The member to remove snippet ban from.
        flags : SnippetUnbanFlags
            The flags for the command. (reason: str, silent: bool)
        """
        assert ctx.guild

        # Check if user is snippet banned
        if not await self.is_snippetbanned(ctx.guild.id, member.id):
            if ctx.interaction:
                await ctx.interaction.followup.send(
                    "User is not snippet banned.",
                    ephemeral=True,
                )
            else:
                await ctx.reply("User is not snippet banned.", mention_author=False)
            return

        # Execute snippet unban with case creation and DM
        await self.moderate_user(
            ctx=ctx,
            case_type=CaseType.SNIPPETUNBAN,
            user=member,
            reason=flags.reason,
            silent=flags.silent,
            dm_action="snippet unbanned",
            actions=[],  # No Discord API actions needed for snippet unban
        )


async def setup(bot: Bot) -> None:
    """Set up the SnippetUnban cog.

    Parameters
    ----------
    bot : Bot
        The bot instance to add the cog to.
    """
    await bot.add_cog(SnippetUnban(bot))
