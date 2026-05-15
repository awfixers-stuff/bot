"""Utility functions for sending responses in info commands."""

import discord
from discord.ext import commands

from bot.core.bot import Bot


async def send_view(
    ctx: commands.Context[Bot],
    view: discord.ui.LayoutView,
    ephemeral: bool = True,
) -> None:
    """Send a LayoutView response, handling both interaction and prefix commands.

    Parameters
    ----------
    ctx : commands.Context[Bot]
        The command context.
    view : discord.ui.LayoutView
        The view to send.
    ephemeral : bool, optional
        Whether the response should be ephemeral (slash commands only), by default True.
    """
    if ctx.interaction:
        if ctx.interaction.response.is_done():
            await ctx.interaction.followup.send(view=view, ephemeral=ephemeral)
        else:
            await ctx.interaction.response.send_message(view=view, ephemeral=ephemeral)
    else:
        await ctx.send(view=view)


async def send_error(
    ctx: commands.Context[Bot],
    error_msg: str,
    ephemeral: bool = True,
) -> None:
    """Send an error message response.

    Parameters
    ----------
    ctx : commands.Context[Bot]
        The command context.
    error_msg : str
        The error message to send.
    ephemeral : bool, optional
        Whether the response should be ephemeral (slash commands only), by default True.
    """
    allowed_mentions = discord.AllowedMentions.none()
    if ctx.interaction:
        if ctx.interaction.response.is_done():
            await ctx.interaction.followup.send(
                content=error_msg,
                ephemeral=ephemeral,
                allowed_mentions=allowed_mentions,
            )
        else:
            await ctx.interaction.response.send_message(
                content=error_msg,
                ephemeral=ephemeral,
                allowed_mentions=allowed_mentions,
            )
    else:
        await ctx.send(content=error_msg, allowed_mentions=allowed_mentions)
