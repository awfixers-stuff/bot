"""Factory for creating moderation service instances.

This module provides a centralized factory for creating moderation service
instances with proper dependency injection, reducing duplication across
moderation cogs.
"""

from typing import TYPE_CHECKING

from bot.services.moderation.case_service import CaseService
from bot.services.moderation.communication_service import CommunicationService
from bot.services.moderation.execution_service import ExecutionService
from bot.services.moderation.moderation_coordinator import ModerationCoordinator

if TYPE_CHECKING:
    from bot.core.bot import Bot
    from bot.database.controllers import CaseController

__all__ = ["ModerationServiceFactory"]


class ModerationServiceFactory:
    """Factory for creating moderation service instances.

    Centralizes the creation logic for moderation services to ensure
    consistent dependency injection across all moderation cogs.
    """

    @staticmethod
    def create_coordinator(
        bot: "Bot",
        case_controller: "CaseController",
    ) -> ModerationCoordinator:
        """Create a ModerationCoordinator with all required services.

        Parameters
        ----------
        bot : Bot
            The bot instance for communication service
        case_controller : CaseController
            The database controller for case management

        Returns
        -------
        ModerationCoordinator
            Fully initialized moderation coordinator

        Examples
        --------
        >>> coordinator = ModerationServiceFactory.create_coordinator(
        ...     self.bot, self.db.case
        ... )
        """
        case_service = CaseService(case_controller)
        communication_service = CommunicationService(bot)
        execution_service = ExecutionService()

        return ModerationCoordinator(
            case_service=case_service,
            communication_service=communication_service,
            execution_service=execution_service,
        )
