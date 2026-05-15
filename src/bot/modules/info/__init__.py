"""Info cog group for Bot Bot."""

from bot.modules.info.info import Info
from bot.modules.info.utils import send_error, send_view
from bot.modules.info.views import InfoPaginatorView

__all__ = [
    "Info",
    "InfoPaginatorView",
    "send_error",
    "send_view",
]
