"""
Moderation case management controller.

This controller manages moderation cases (bans, kicks, timeouts, etc.) with
automatic case numbering, status tracking, and audit logging.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, cast

from loguru import logger
from sqlalchemy import func, or_, select
from sqlalchemy.orm import noload

from bot.database.controllers.base import BaseController
from bot.database.models import Case
from bot.database.models.enums import CaseType as DBCaseType

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from bot.cache import AsyncCacheBackendProtocol
    from bot.database.service import DatabaseService

# Case lookup by number; invalidated on update_case_by_number.
CASE_BY_NUMBER_CACHE_TTL_SEC = 1800.0  # 30 min


def _case_cache_key(case_number: int) -> str:
    """Return cache key for case-by-number lookup."""
    return f"case:by_number:{case_number}"


def _wrap_case_for_cache(value: Case | None) -> dict[str, Any]:
    """Wrap optional Case for backend (distinguish cached None from miss)."""
    if value is None:
        return {"_v": None}
    return {"_v": value.model_dump(mode="json")}


def _unwrap_case_from_cache(raw: Any) -> Case | None:
    """Unwrap optional Case from backend."""
    if raw is None or not isinstance(raw, dict):
        return None
    raw_dict = cast(dict[str, Any], raw)
    v = raw_dict.get("_v")
    if v is None:
        return None
    return Case.model_validate(cast(dict[str, Any], v))


class CaseController(BaseController[Case]):
    """Clean Case controller using the new BaseController pattern."""

    def __init__(
        self,
        db: DatabaseService | None = None,
        cache_backend: AsyncCacheBackendProtocol | None = None,
    ) -> None:
        """Initialize the case controller.

        Parameters
        ----------
        db : DatabaseService | None, optional
            The database service instance. If None, uses the default service.
        cache_backend : AsyncCacheBackendProtocol | None, optional
            Optional cache backend (Valkey/in-memory) for case-by-number lookups.
        """
        super().__init__(Case, db)
        self._cache_backend = cache_backend

    async def get_case_by_id(self, case_id: int) -> Case | None:
        """Get a case by its ID.

        Returns
        -------
        Case | None
            The case if found, None otherwise.
        """
        return await self.get_by_id(case_id)

    async def get_cases_by_user(self, user_id: int) -> list[Case]:
        """Get all cases for a specific user.

        Returns
        -------
        list[Case]
            List of all cases for the user.
        """
        return await self.find_all(filters=Case.case_user_id == user_id)

    async def get_active_cases_by_user(self, user_id: int) -> list[Case]:
        """Get all active cases for a specific user.

        Returns
        -------
        list[Case]
            List of active cases for the user.
        """
        return await self.find_all(
            filters=(Case.case_user_id == user_id) & (Case.case_status),
        )

    async def create_case(
        self,
        case_type: str,
        case_user_id: int,
        case_moderator_id: int,
        case_reason: str | None = None,
        case_status: bool = True,
        **kwargs: Any,
    ) -> Case:
        """Create a new case with auto-generated case number.

        Generates the next sequential case_number using MAX(case_number) + 1.

        Parameters
        ----------
        case_type : str
            The type of case (from CaseType enum value)
        case_user_id : int
            Discord ID of the user being moderated
        case_moderator_id : int
            Discord ID of the moderator
        case_reason : str | None
            Reason for the moderation action
        case_status : bool
            Whether the case is active (default True)
        **kwargs : Any
            Additional case fields (e.g., case_expires_at, case_metadata, mod_log_message_id)

        Returns
        -------
        Case
            The newly created case with auto-generated case number.

        Notes
        -----
        - For expiring cases, use `case_expires_at` (datetime) in kwargs
        - Do NOT pass `duration` - convert to `case_expires_at` before calling this method
        - Case numbers are auto-generated using MAX(case_number) + 1
        """

        async def _create(session: AsyncSession) -> Case:
            # Get next case number
            result = await session.execute(
                select(func.max(Case.case_number)),
            )
            max_number: int | None = result.scalar()
            case_number = (max_number or 0) + 1
            logger.info(f"Generated case number {case_number}")

            # Build case data dict
            case_data: dict[str, Any] = {
                "case_type": case_type,
                "case_user_id": case_user_id,
                "case_moderator_id": case_moderator_id,
                "case_status": case_status,
                "case_number": case_number,
            }

            if case_reason is not None:
                case_data["case_reason"] = case_reason

            # Filter out 'id' to prevent manual ID assignment
            filtered_kwargs = {k: v for k, v in kwargs.items() if k != "id"}
            if "id" in kwargs:
                logger.warning(
                    f"Ignoring 'id' in kwargs (id={kwargs['id']}) - database will auto-generate the ID",
                )
            case_data.update(filtered_kwargs)

            case = Case(**case_data)
            session.add(case)
            await session.flush()
            await session.refresh(case)
            logger.success(
                f"Case created successfully: ID={case.id}, number={case.case_number}, expires_at={case.case_expires_at}",
            )
            return case

        return await self.with_session(_create)

    async def update_case(self, case_id: int, **kwargs: Any) -> Case | None:
        """Update a case by ID.

        Returns
        -------
        Case | None
            The updated case, or None if not found.
        """
        return await self.update_by_id(case_id, **kwargs)

    async def update_mod_log_message_id(
        self,
        case_id: int,
        message_id: int,
    ) -> Case | None:
        """Update the mod log message ID for a case.

        Parameters
        ----------
        case_id : int
            The case ID to update.
        message_id : int
            The Discord message ID from the mod log.

        Returns
        -------
        Case | None
            The updated case, or None if not found.
        """
        return await self.update_by_id(case_id, mod_log_message_id=message_id)

    async def close_case(self, case_id: int) -> Case | None:
        """Close a case by setting its status to False.

        Returns
        -------
        Case | None
            The updated case, or None if not found.
        """
        return await self.update_by_id(case_id, case_status=False)

    async def delete_case(self, case_id: int) -> bool:
        """Delete a case by ID.

        Returns
        -------
        bool
            True if deleted successfully, False otherwise.
        """
        return await self.delete_by_id(case_id)

    async def get_all_cases(self) -> list[Case]:
        """Get all cases.

        Returns
        -------
        list[Case]
            List of all cases.
        """
        return await self.find_all()

    async def get_cases_by_type(self, case_type: str) -> list[Case]:
        """Get all cases of a specific type.

        Returns
        -------
        list[Case]
            List of cases matching the specified type.
        """
        return await self.find_all(filters=Case.case_type == case_type)

    async def get_recent_cases(self) -> list[Case]:
        """Get all cases.

        Returns
        -------
        list[Case]
            List of all cases.
        """
        return await self.find_all()

    async def get_case_count(self) -> int:
        """Get the total number of cases.

        Returns
        -------
        int
            The total count of cases.
        """
        return await self.count()

    async def is_user_under_restriction(
        self,
        user_id: int | None = None,
        **kwargs: Any,
    ) -> bool:
        """Check if a user is under any active restriction.

        Returns
        -------
        bool
            True if user is under restriction, False otherwise.
        """
        if user_id is None and "user_id" in kwargs:
            user_id = kwargs["user_id"]

        if user_id is None:
            return False

        active_cases = await self.get_active_cases_by_user(user_id)
        return bool(active_cases)

    async def get_case_by_number(self, case_number: int) -> Case | None:
        """Get a case by its case number.

        Uses optional cache backend (Valkey when connected) to avoid repeated DB
        hits for the same case. Cache is invalidated on update_case_by_number.

        Returns
        -------
        Case | None
            The case if found, None otherwise.
        """
        key = _case_cache_key(case_number)
        if self._cache_backend is not None:
            raw = await self._cache_backend.get(key)
            if raw is not None:
                return _unwrap_case_from_cache(raw)
        case = await self.find_one(
            filters=Case.case_number == case_number,
        )
        if self._cache_backend is not None:
            await self._cache_backend.set(
                key,
                _wrap_case_for_cache(case),
                ttl_sec=CASE_BY_NUMBER_CACHE_TTL_SEC,
            )
        return case

    async def get_cases_by_options(
        self,
        options: dict[str, Any] | None = None,
    ) -> list[Case]:
        """Get cases by various filter options.

        Returns
        -------
        list[Case]
            List of cases matching the specified options.
        """
        filters: list[Any] = []

        if options is None:
            options = {}

        if "user_id" in options:
            filters.append(Case.case_user_id == options["user_id"])
        if "moderator_id" in options:
            filters.append(Case.case_moderator_id == options["moderator_id"])
        if "case_type" in options:
            filters.append(Case.case_type == options["case_type"])
        if "status" in options:
            filters.append(Case.case_status == options["status"])

        if not filters:
            return await self.find_all()
        return await self.find_all(filters=filters)

    async def update_case_by_number(
        self,
        case_number: int,
        **kwargs: Any,
    ) -> Case | None:
        """Update a case by case number.

        Invalidates the case-by-number cache so the next get_case_by_number
        sees fresh data.

        Returns
        -------
        Case | None
            The updated case, or None if not found.
        """
        case = await self.get_case_by_number(case_number)
        if case is None:
            return None

        updated = await self.update_by_id(case.id, **kwargs)
        if updated is not None and self._cache_backend is not None:
            await self._cache_backend.delete(_case_cache_key(case_number))
        return updated

    async def get_latest_case_by_user(self, user_id: int) -> Case | None:
        """Get the most recent case for a user.

        Returns
        -------
        Case | None
            The most recent case if found, None otherwise.
        """
        return await self.find_one(
            filters=Case.case_user_id == user_id,
            order_by=[Case.id.desc()],  # type: ignore[attr-defined]
        )

    async def get_latest_jail_case(self, user_id: int) -> Case | None:
        """Get the most recent JAIL case for a user.

        Used when unjailing to restore roles from the case_user_roles stored at jail time.

        Returns
        -------
        Case | None
            The most recent JAIL case if found, None otherwise.
        """
        return await self.find_one(
            filters=(Case.case_user_id == user_id)
            & (Case.case_type == DBCaseType.JAIL),
            order_by=[Case.id.desc()],  # type: ignore[attr-defined]
        )

    async def get_latest_jail_or_unjail_case(
        self,
        user_id: int,
    ) -> Case | None:
        """Get the most recent JAIL or UNJAIL case for a user.

        Used to determine if a user is currently jailed: if the latest of these
        is JAIL, they are jailed; if UNJAIL or none, they are not.

        Returns
        -------
        Case | None
            The most recent JAIL or UNJAIL case if found, None otherwise.
        """
        return await self.find_one(
            filters=(Case.case_user_id == user_id)
            & (
                or_(
                    Case.case_type == DBCaseType.JAIL,  # type: ignore[arg-type]
                    Case.case_type == DBCaseType.UNJAIL,  # type: ignore[arg-type]
                )
            ),
            order_by=[Case.id.desc()],  # type: ignore[attr-defined]
        )

    async def get_latest_snippet_ban_or_unban_case(
        self,
        user_id: int,
    ) -> Case | None:
        """Get the most recent SNIPPETBAN or SNIPPETUNBAN case for a user.

        Used to determine if a user is currently snippet banned: if the latest
        of these is SNIPPETBAN, they are banned; if SNIPPETUNBAN or none, they
        are not.

        Returns
        -------
        Case | None
            The most recent SNIPPETBAN or SNIPPETUNBAN case if found, None otherwise.
        """
        return await self.find_one(
            filters=(Case.case_user_id == user_id)
            & (
                or_(
                    Case.case_type == DBCaseType.SNIPPETBAN,  # type: ignore[arg-type]
                    Case.case_type == DBCaseType.SNIPPETUNBAN,  # type: ignore[arg-type]
                )
            ),
            order_by=[Case.id.desc()],  # type: ignore[attr-defined]
        )

    async def set_tempban_expired(self, case_id: int) -> bool:
        """Mark a tempban case as processed after the user has been unbanned.

        This sets case_processed=True to indicate the expiration has been handled.
        The case_status remains True (the case is still valid, just completed).

        Returns
        -------
        bool
            True if the case was updated, False if not found
        """
        logger.debug(
            f"Marking tempban case {case_id} as processed (setting case_processed=True)",
        )
        result = await self.update_by_id(case_id, case_processed=True)
        success = result is not None
        if success:
            logger.debug(
                f"Case {case_id} marked as processed (case_processed=True, case_status unchanged)",
            )
        return success

    async def get_expired_tempbans(self) -> list[Case]:
        """Get tempban cases that have expired but haven't been processed yet.

        Returns
        -------
        list[Case]
            List of expired unprocessed tempban cases where case_expires_at is in the past,
            case_processed=False, and case_status=True.
        """
        now = datetime.now(UTC)
        logger.trace(
            f"Checking for unprocessed expired tempbans, current time: {now}",
        )

        expired_cases = await self.find_all(
            filters=(
                (Case.case_type == DBCaseType.TEMPBAN.value)
                & (Case.case_status == True)  # noqa: E712
                & (Case.case_processed == False)  # noqa: E712
                & (Case.case_expires_at.is_not(None))  # type: ignore[attr-defined]
                & (Case.case_expires_at < now)  # type: ignore[arg-type]
            ),
        )

        if expired_cases:
            logger.info(
                f"Found {len(expired_cases)} unprocessed expired tempbans",
            )
            for case in expired_cases:
                logger.debug(
                    f"Unprocessed expired tempban: case_id={case.id}, user={case.case_user_id}, "
                    f"expires_at={case.case_expires_at}, processed={case.case_processed}",
                )
        else:
            logger.trace("No unprocessed expired tempbans found")

        return expired_cases

    async def get_case_count_by_user(self, user_id: int) -> int:
        """Get the total number of cases for a specific user.

        Returns
        -------
        int
            The total count of cases for the user.
        """
        return await self.count(filters=Case.case_user_id == user_id)

    async def get_cases_by_moderator(self, moderator_id: int) -> list[Case]:
        """Get all cases moderated by a specific user.

        Returns
        -------
        list[Case]
            List of cases moderated by the user.
        """
        return await self.find_all(
            filters=Case.case_moderator_id == moderator_id,
        )

    async def get_expired_cases(self) -> list[Case]:
        """Get all expired cases (any type) that haven't been processed yet.

        Returns
        -------
        list[Case]
            List of expired unprocessed cases where case_expires_at is in the past,
            case_processed=False, and case_status=True.
        """
        now = datetime.now(UTC)

        return await self.find_all(
            filters=(
                (Case.case_status == True)  # noqa: E712
                & (Case.case_processed == False)  # noqa: E712
                & (Case.case_expires_at.is_not(None))  # type: ignore[attr-defined]
                & (Case.case_expires_at < now)  # type: ignore[arg-type]
            ),
        )
