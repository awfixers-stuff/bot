"""
Code snippet storage and management controller.

This controller manages reusable code snippets, allowing
users to save and retrieve frequently used code blocks and text templates.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import desc

from bot.database.controllers.base import BaseController
from bot.database.models import Snippet

if TYPE_CHECKING:
    from bot.database.service import DatabaseService


class SnippetController(BaseController[Snippet]):
    """Clean Snippet controller using the new BaseController pattern."""

    def __init__(self, db: DatabaseService | None = None) -> None:
        """Initialize the snippet controller.

        Parameters
        ----------
        db : DatabaseService | None, optional
            The database service instance. If None, uses the default service.
        """
        super().__init__(Snippet, db)

    async def get_snippet_by_id(self, snippet_id: int) -> Snippet | None:
        """Get a snippet by its ID.

        Parameters
        ----------
        snippet_id : int
            The ID of the snippet to retrieve.

        Returns
        -------
        Snippet | None
            The snippet if found, None otherwise.
        """
        return await self.get_by_id(snippet_id)

    async def get_snippet_by_name(self, name: str) -> Snippet | None:
        """Get a snippet by name.

        Parameters
        ----------
        name : str
            The name of the snippet.

        Returns
        -------
        Snippet | None
            The snippet if found, None otherwise.
        """
        return await self.find_one(filters=Snippet.snippet_name == name)

    async def get_all_snippets(
        self,
        order_by: Any | None = None,
    ) -> list[Snippet]:
        """Get all snippets, optionally ordered.

        Parameters
        ----------
        order_by : Any | None, optional
            Optional ordering expression (e.g., desc(Snippet.uses)).

        Returns
        -------
        list[Snippet]
            List of all snippets.
        """
        return await self.find_all(order_by=order_by)

    async def create_snippet(
        self,
        snippet_name: str,
        snippet_content: str,
        snippet_user_id: int,
        alias: str | None = None,
        **kwargs: Any,
    ) -> Snippet:
        """Create a new snippet.

        Parameters
        ----------
        snippet_name : str
            The name of the snippet.
        snippet_content : str
            The content of the snippet.
        snippet_user_id : int
            The ID of the user creating the snippet.
        alias : str | None, optional
            Optional alias name for the snippet.
        **kwargs : Any
            Additional fields to set on the snippet.

        Returns
        -------
        Snippet
            The newly created snippet.
        """
        return await self.create(
            snippet_name=snippet_name,
            snippet_content=snippet_content,
            snippet_user_id=snippet_user_id,
            alias=alias,
            uses=0,
            locked=False,
            **kwargs,
        )

    async def update_snippet_by_id(
        self,
        snippet_id: int,
        **kwargs: Any,
    ) -> Snippet | None:
        """Update a snippet by ID.

        Parameters
        ----------
        snippet_id : int
            The ID of the snippet to update.
        **kwargs : Any
            Fields to update on the snippet.

        Returns
        -------
        Snippet | None
            The updated snippet, or None if not found.
        """
        return await self.update_by_id(snippet_id, **kwargs)

    async def delete_snippet_by_id(self, snippet_id: int) -> bool:
        """Delete a snippet by ID.

        Parameters
        ----------
        snippet_id : int
            The ID of the snippet to delete.

        Returns
        -------
        bool
            True if deleted successfully, False otherwise.
        """
        return await self.delete_by_id(snippet_id)

    async def get_snippets_by_creator(self, creator_id: int) -> list[Snippet]:
        """Get all snippets created by a specific user.

        Parameters
        ----------
        creator_id : int
            The ID of the user who created the snippets.

        Returns
        -------
        list[Snippet]
            List of snippets created by the user.
        """
        return await self.find_all(
            filters=Snippet.snippet_user_id == creator_id,
        )

    async def search_snippets(self, search_term: str) -> list[Snippet]:
        """Search snippets by name or content.

        Uses Python-side filtering for case-insensitive search.
        For production use with large datasets, consider implementing
        database-level ILIKE queries via custom SQL.

        Parameters
        ----------
        search_term : str
            The search term to match against snippet names and content.

        Returns
        -------
        list[Snippet]
            List of snippets matching the search term.
        """
        all_snippets = await self.get_all_snippets()
        search_lower = search_term.lower()
        return [
            snippet
            for snippet in all_snippets
            if (
                search_lower in snippet.snippet_name.lower()
                or (
                    snippet.snippet_content
                    and search_lower in snippet.snippet_content.lower()
                )
            )
        ]

    async def get_snippet_count(self) -> int:
        """Get the total number of snippets.

        Returns
        -------
        int
            The total count of snippets.
        """
        return await self.count()

    async def create_snippet_alias(
        self,
        original_name: str,
        alias_name: str,
    ) -> Snippet:
        """Create a snippet alias.

        Returns
        -------
        Snippet
            The newly created alias snippet.

        Raises
        ------
        ValueError
            If the original snippet is not found.
        """
        original = await self.get_snippet_by_name(original_name)
        if not original:
            error_msg = f"Snippet '{original_name}' not found"
            raise ValueError(error_msg)

        return await self.create(
            snippet_name=alias_name,
            snippet_content=original.snippet_content,
            snippet_user_id=original.snippet_user_id,
            uses=0,
            locked=original.locked,
            alias=original_name,
        )

    async def get_snippet_count_by_creator(self, creator_id: int) -> int:
        """Get the number of snippets created by a user.

        Parameters
        ----------
        creator_id : int
            The ID of the user.

        Returns
        -------
        int
            The count of snippets created by the user.
        """
        return await self.count(
            filters=Snippet.snippet_user_id == creator_id,
        )

    async def toggle_snippet_lock_by_id(self, snippet_id: int) -> Snippet | None:
        """Toggle the locked status of a snippet by ID.

        Parameters
        ----------
        snippet_id : int
            The ID of the snippet to toggle.

        Returns
        -------
        Snippet | None
            The updated snippet, or None if not found.
        """
        snippet = await self.get_snippet_by_id(snippet_id)
        if snippet is None:
            return None
        return await self.update_by_id(snippet_id, locked=not snippet.locked)

    async def increment_snippet_uses(self, snippet_id: int) -> Snippet | None:
        """Increment the usage count of a snippet.

        Parameters
        ----------
        snippet_id : int
            The ID of the snippet to increment uses for.

        Returns
        -------
        Snippet | None
            The updated snippet, or None if not found.
        """
        snippet = await self.get_snippet_by_id(snippet_id)
        if snippet is None:
            return None
        return await self.update_by_id(snippet_id, uses=snippet.uses + 1)

    async def get_popular_snippets(
        self,
        limit: int = 10,
    ) -> list[Snippet]:
        """Get the most popular snippets by usage count.

        Uses database-level ordering for better performance.

        Parameters
        ----------
        limit : int, optional
            Maximum number of snippets to return. Defaults to 10.

        Returns
        -------
        list[Snippet]
            List of snippets sorted by usage count (most popular first).
        """
        return await self.find_all(
            order_by=desc(Snippet.__table__.c.uses),  # type: ignore[attr-defined]
            limit=limit,
        )

    async def get_snippets_by_alias(self, alias: str) -> list[Snippet]:
        """Get snippets by alias.

        Parameters
        ----------
        alias : str
            The alias name to search for.

        Returns
        -------
        list[Snippet]
            List of snippets with the specified alias.
        """
        return await self.find_all(filters=Snippet.alias == alias)

    async def get_all_aliases(self) -> list[Snippet]:
        """Get all aliases.

        Returns
        -------
        list[Snippet]
            List of all alias snippets.
        """
        return await self.find_all(
            filters=Snippet.alias.is_not(None),  # type: ignore[attr-defined]
        )
