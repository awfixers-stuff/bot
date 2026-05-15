"""
User reporting system for Discord servers.

This module provides an anonymous reporting system that allows users to report
issues, users, or content to server moderators through a modal interface.
"""

import discord
from discord import app_commands

from bot.core.base_cog import BaseCog
from bot.core.bot import Bot
from bot.ui.modals.report import ReportModal


class Report(BaseCog):
    """Discord cog for user reporting functionality."""

    def __init__(self, bot: Bot) -> None:
        """Initialize the Report cog.

        Parameters
        ----------
        bot : Bot
            The bot instance to attach this cog to.
        """
        super().__init__(bot)

    @app_commands.command(name="report")
    @app_commands.guild_only()
    async def report(self, interaction: discord.Interaction) -> None:
        """
        Report a user or issue anonymously.

        Parameters
        ----------
        interaction : discord.Interaction
            The interaction that triggered the command.
        """
        modal = ReportModal(bot=self.bot)

        await interaction.response.send_modal(modal)


async def setup(bot: Bot) -> None:
    """Set up the Report cog.

    Parameters
    ----------
    bot : Bot
        The bot instance to add the cog to.
    """
    await bot.add_cog(Report(bot))
