"""View components for Discord UI interactions.

This module contains reusable view components for complex Discord interactions.
"""

from bot.ui.views.confirmation import (
    BaseConfirmationView,
    ConfirmationDanger,
    ConfirmationNormal,
)
from bot.ui.views.tldr import TldrPaginatorView

__all__ = [
    "BaseConfirmationView",
    "ConfirmationDanger",
    "ConfirmationNormal",
    "TldrPaginatorView",
]
