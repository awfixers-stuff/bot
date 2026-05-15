"""
Starboard message highlighting controller.

This controller manages starboard functionality, allowing
popular messages to be automatically posted to designated starboard channels
based on reaction thresholds and user preferences.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bot.database.controllers.base import BaseController
from bot.database.models import Starboard, StarboardMessage

if TYPE_CHECKING:
    from bot.database.service import DatabaseService


class StarboardController(BaseController[Starboard]):
    """Clean Starboard controller using the new BaseController pattern."""

    def __init__(self, db: DatabaseService | None = None) -> None:
        """Initialize the starboard controller.

        Parameters
        ----------
        db : DatabaseService | None, optional
            The database service instance. If None, uses the default service.
        """
        super().__init__(Starboard, db)

    async def get_starboard(self) -> Starboard | None:
        """Get the starboard configuration.

        Since the bot operates on a single guild, there is one starboard config.
        This returns the first (and only) record.

        Returns
        -------
        Starboard | None
            The starboard configuration if found, None otherwise.
        """
        result = await self.find_all(limit=1)
        return result[0] if result else None

    async def get_or_create_starboard(
        self,
        **defaults: Any,
    ) -> Starboard:
        """Get starboard configuration, or create it with defaults if it doesn't exist.

        Returns
        -------
        Starboard
            The starboard configuration (existing or newly created).
        """
        starboard = await self.get_starboard()
        if starboard is not None:
            return starboard
        return await self.create(**defaults)

    async def update_starboard(self, **updates: Any) -> Starboard | None:
        """Update starboard configuration.

        Returns
        -------
        Starboard | None
            The updated starboard configuration, or None if not found.
        """
        starboard = await self.get_starboard()
        if starboard is None:
            return None
        return await self.update_by_id(starboard.id, **updates)

    async def delete_starboard(self) -> bool:
        """Delete starboard configuration.

        Returns
        -------
        bool
            True if deleted successfully, False otherwise.
        """
        starboard = await self.get_starboard()
        return False if starboard is None else await self.delete_by_id(starboard.id)

    async def create_or_update_starboard(
        self,
        **kwargs: Any,
    ) -> Starboard:
        """Create or update starboard configuration.

        Returns
        -------
        Starboard
            The starboard configuration (created or updated).
        """
        existing = await self.get_starboard()
        if existing:
            for key, value in kwargs.items():
                setattr(existing, key, value)
            updated = await self.update_by_id(existing.id, **kwargs)
            return updated if updated is not None else existing
        return await self.create(**kwargs)


class StarboardMessageController(BaseController[StarboardMessage]):
    """Clean StarboardMessage controller using the new BaseController pattern."""

    def __init__(self, db: DatabaseService | None = None) -> None:
        """Initialize the starboard message controller.

        Parameters
        ----------
        db : DatabaseService | None, optional
            The database service instance. If None, uses the default service.
        """
        super().__init__(StarboardMessage, db)

    async def get_message_by_id(self, message_id: int) -> StarboardMessage | None:
        """Get a starboard message by its ID (the original Discord message ID).

        Returns
        -------
        StarboardMessage | None
            The starboard message if found, None otherwise.
        """
        return await self.get_by_id(message_id)

    async def get_message_by_original(
        self,
        original_message_id: int,
    ) -> StarboardMessage | None:
        """Get a starboard message by its original message ID.

        Returns
        -------
        StarboardMessage | None
            The starboard message if found, None otherwise.
        """
        return await self.find_one(
            filters=StarboardMessage.id == original_message_id,
        )

    async def get_messages_by_channel(
        self,
        channel_id: int,
    ) -> list[StarboardMessage]:
        """Get all starboard messages in a specific channel.

        Returns
        -------
        list[StarboardMessage]
            List of all starboard messages in the channel.
        """
        return await self.find_all(
            filters=StarboardMessage.message_channel_id == channel_id,
        )

    async def create_starboard_message(
        self,
        original_message_id: int,
        starboard_message_id: int,
        channel_id: int,
        star_count: int = 1,
        **kwargs: Any,
    ) -> StarboardMessage:
        """Create a new starboard message.

        Returns
        -------
        StarboardMessage
            The newly created starboard message.
        """
        return await self.create(
            id=original_message_id,
            starboard_message_id=starboard_message_id,
            message_channel_id=channel_id,
            star_count=star_count,
            **kwargs,
        )

    async def update_star_count(
        self,
        message_id: int,
        new_star_count: int,
    ) -> StarboardMessage | None:
        """Update the star count for a starboard message.

        Returns
        -------
        StarboardMessage | None
            The updated starboard message, or None if not found.
        """
        return await self.update_by_id(message_id, star_count=new_star_count)

    async def delete_starboard_message(self, message_id: int) -> bool:
        """Delete a starboard message.

        Returns
        -------
        bool
            True if deleted successfully, False otherwise.
        """
        return await self.delete_by_id(message_id)

    async def get_top_messages(
        self,
        limit: int = 10,
    ) -> list[StarboardMessage]:
        """Get top starboard messages by star count.

        Returns
        -------
        list[StarboardMessage]
            List of top starboard messages sorted by star count.
        """
        return await self.find_all(
            order_by=[StarboardMessage.star_count.desc()],  # type: ignore[attr-defined]
            limit=limit,
        )

    async def get_message_count(self) -> int:
        """Get the total number of starboard messages.

        Returns
        -------
        int
            The total count of starboard messages.
        """
        return await self.count()

    async def get_starboard_message_by_id(
        self,
        message_id: int,
    ) -> StarboardMessage | None:
        """Get a starboard message by its ID - alias for get_message_by_id.

        Returns
        -------
        StarboardMessage | None
            The starboard message if found, None otherwise.
        """
        return await self.get_message_by_id(message_id)

    async def create_or_update_starboard_message(
        self,
        **kwargs: Any,
    ) -> StarboardMessage:
        """Create or update a starboard message.

        Returns
        -------
        StarboardMessage
            The starboard message (created or updated).
        """
        if "id" in kwargs:
            existing = await self.get_message_by_original(kwargs["id"])
            if existing:
                for key, value in kwargs.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
                updated = await self.update_by_id(existing.id, **kwargs)
                return updated if updated is not None else existing

        return await self.create(**kwargs)
