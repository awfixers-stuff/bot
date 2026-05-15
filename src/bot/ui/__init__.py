"""UI components for the Bot Discord bot.

This module contains all user interface components including:
- Embeds and embed creators
- Buttons and interactive components
- Views for complex interactions
- Modals for user input
- Help system components
"""

from bot.ui.buttons import GithubButton, XkcdButtons
from bot.ui.embeds import EmbedCreator, EmbedType
from bot.ui.modals import ReportModal
from bot.ui.views import (
    BaseConfirmationView,
    ConfirmationDanger,
    ConfirmationNormal,
    TldrPaginatorView,
)

__all__ = [
    # Embeds
    "EmbedCreator",
    "EmbedType",
    # Buttons
    "GithubButton",
    "XkcdButtons",
    # Views
    "BaseConfirmationView",
    "ConfirmationDanger",
    "ConfirmationNormal",
    "TldrPaginatorView",
    # Modals
    "ReportModal",
]
