"""Hot reload cog for file watching and automatic reloading."""

from loguru import logger

from bot.core.bot import Bot
from bot.services.hot_reload.service import HotReload


async def setup(bot: Bot) -> None:
    """Cog setup for hot reload.

    Parameters
    ----------
    bot : Bot
        The bot instance.
    """
    await bot.add_cog(HotReload(bot))
    logger.trace("Hot reload cog loaded")
