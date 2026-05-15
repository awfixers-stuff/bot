"""
Dynamic permission system controllers.

Provides database operations for the flexible permission system that allows
servers to customize their permission levels and role assignments.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

import discord
from loguru import logger
from sqlmodel import select

from bot.cache import TTLCache
from bot.database.controllers.base import BaseController
from bot.database.models.models import (
    PermissionAssignment,
    PermissionCommand,
    PermissionRank,
)
from bot.services.sentry import capture_exception_safe

if TYPE_CHECKING:
    from bot.cache import AsyncCacheBackendProtocol
    from bot.database.service import DatabaseService

PERM_KEY_PREFIX = "perm:"
# Ranks and assignments: setup-once; invalidated on config change.
PERM_RANKS_TTL = 7200.0  # 2 hours
# User rank (derived from roles); invalidated when assignments change.
PERM_USER_RANK_TTL = 7200.0  # 2 hours


class PermissionRankController(BaseController[PermissionRank]):
    """Controller for managing permission ranks."""

    # Shared cache for permission ranks when no backend
    _ranks_cache: TTLCache = TTLCache(ttl=PERM_RANKS_TTL, max_size=1000)
    _all_ranks_cache: TTLCache = TTLCache(ttl=PERM_RANKS_TTL, max_size=5)

    def __init__(
        self,
        db: DatabaseService | None = None,
        cache_backend: AsyncCacheBackendProtocol | None = None,
    ) -> None:
        """Initialize the permission rank controller.

        Parameters
        ----------
        db : DatabaseService | None, optional
            The database service instance. If None, uses the default service.
        cache_backend : AsyncCacheBackendProtocol | None, optional
            Optional cache backend (Valkey/in-memory) for permission ranks.
        """
        super().__init__(PermissionRank, db)
        self._backend = cache_backend

    async def create_permission_rank(
        self,
        rank: int,
        name: str,
        description: str | None = None,
    ) -> PermissionRank:
        """Create a new permission rank.

        Returns
        -------
        PermissionRank
            The newly created permission rank.
        """
        logger.debug(f"Creating permission rank: rank={rank}, name={name}")
        try:
            result = await self.create(
                rank=rank,
                name=name,
                description=description,
            )
            # Invalidate cache
            if self._backend is not None:
                await self._backend.delete(f"{PERM_KEY_PREFIX}permission_ranks")
                if result.id is not None:
                    await self._backend.delete(
                        f"{PERM_KEY_PREFIX}permission_rank:{result.id}",
                    )
            else:
                self._all_ranks_cache.invalidate("permission_ranks")
                if result.id:
                    self._ranks_cache.invalidate(f"permission_rank:{result.id}")
            logger.trace("Invalidated permission rank cache")
        except Exception as e:
            logger.error(f"Error creating permission rank {rank}: {e}")
            capture_exception_safe(
                e,
                extra_context={
                    "operation": "create_permission_rank",
                    "rank": str(rank),
                },
            )
            raise
        else:
            logger.debug(f"Successfully created permission rank {rank}")
            return result

    async def get_all_permission_ranks(self) -> list[PermissionRank]:
        """Get all permission ranks.

        Returns
        -------
        list[PermissionRank]
            List of permission ranks ordered by rank value.
        """
        cache_key = f"{PERM_KEY_PREFIX}permission_ranks"
        if self._backend is not None:
            raw = await self._backend.get(cache_key)
            if raw is not None and isinstance(raw, list):
                logger.trace("Cache hit for permission ranks")
                items = cast(list[dict[str, Any]], raw)
                return [PermissionRank.model_validate(d) for d in items]
        else:
            cached = self._all_ranks_cache.get("permission_ranks")
            if cached is not None:
                logger.trace("Cache hit for permission ranks")
                return cached

        result = await self.find_all(order_by=PermissionRank.rank)
        if self._backend is not None:
            await self._backend.set(
                cache_key,
                [m.model_dump() for m in result],
                ttl_sec=PERM_RANKS_TTL,
            )
        else:
            self._all_ranks_cache.set("permission_ranks", result)
        logger.trace("Cached permission ranks")
        return result

    async def get_permission_rank(self, rank: int) -> PermissionRank | None:
        """Get a specific permission rank by its numeric level.

        Returns
        -------
        PermissionRank | None
            The permission rank if found, None otherwise.
        """
        return await self.find_one(filters=PermissionRank.rank == rank)

    async def update_permission_rank(
        self,
        rank: int,
        name: str | None = None,
        description: str | None = discord.utils.MISSING,
    ) -> PermissionRank | None:
        """Update a permission rank.

        Pass ``description=None`` to clear the description; omit the argument
        to leave it unchanged.

        Returns
        -------
        PermissionRank | None
            The updated permission rank, or None if not found.
        """
        record = await self.find_one(filters=PermissionRank.rank == rank)
        if not record:
            return None

        update_data: dict[str, str | None] = {}
        if name is not None:
            update_data["name"] = name
        if description is not discord.utils.MISSING:
            update_data["description"] = description

        result = await self.update_by_id(record.id, **update_data)
        # Invalidate cache
        if self._backend is not None:
            await self._backend.delete(f"{PERM_KEY_PREFIX}permission_ranks")
            if record.id is not None:
                await self._backend.delete(
                    f"{PERM_KEY_PREFIX}permission_rank:{record.id}",
                )
        else:
            self._all_ranks_cache.invalidate("permission_ranks")
            if record.id:
                self._ranks_cache.invalidate(f"permission_rank:{record.id}")
        logger.trace("Invalidated permission rank cache")
        return result

    async def bulk_create_permission_ranks(
        self,
        ranks_data: list[dict[str, Any]],
    ) -> list[PermissionRank]:
        """Bulk create multiple permission ranks in a single transaction.

        Parameters
        ----------
        ranks_data : list[dict[str, Any]]
            List of rank data dictionaries, each containing rank, name, description

        Returns
        -------
        list[PermissionRank]
            List of created permission rank instances
        """
        logger.debug(f"Bulk creating {len(ranks_data)} permission ranks")
        try:
            async with self.db.session() as session:
                instances: list[PermissionRank] = []
                for data in ranks_data:
                    instance = self.model(**data)
                    session.add(instance)
                    instances.append(instance)

                await session.commit()

                for instance in instances:
                    try:
                        await session.refresh(instance)
                    except Exception as e:
                        logger.warning(f"Refresh failed for {self.model.__name__}: {e}")

                for instance in instances:
                    session.expunge(instance)

                # Invalidate cache
                if self._backend is not None:
                    await self._backend.delete(f"{PERM_KEY_PREFIX}permission_ranks")
                    logger.trace("Invalidated permission ranks cache")
                else:
                    self._all_ranks_cache.invalidate("permission_ranks")
                    logger.trace("Invalidated permission ranks cache")

                logger.debug(
                    f"Successfully bulk created {len(instances)} permission ranks",
                )
                return instances

        except Exception as e:
            logger.error(f"Error bulk creating permission ranks: {e}")
            capture_exception_safe(
                e,
                extra_context={
                    "operation": "bulk_create_permission_ranks",
                    "count": str(len(ranks_data)),
                },
            )
            raise

    async def delete_permission_rank(self, rank: int) -> bool:
        """Delete a permission rank.

        Returns
        -------
        bool
            True if deleted successfully, False otherwise.
        """
        record = await self.find_one(filters=PermissionRank.rank == rank)
        deleted_count = await self.delete_where(
            filters=PermissionRank.rank == rank,
        )
        if deleted_count > 0:
            if self._backend is not None:
                await self._backend.delete(f"{PERM_KEY_PREFIX}permission_ranks")
                if record is not None and record.id is not None:
                    await self._backend.delete(
                        f"{PERM_KEY_PREFIX}permission_rank:{record.id}",
                    )
            else:
                self._all_ranks_cache.invalidate("permission_ranks")
                if record and record.id:
                    self._ranks_cache.invalidate(f"permission_rank:{record.id}")
            logger.trace("Invalidated permission rank cache")
        return deleted_count > 0


class PermissionAssignmentController(BaseController[PermissionAssignment]):
    """Controller for managing permission assignments."""

    # Shared cache when no backend
    _assignments_cache: TTLCache = TTLCache(ttl=PERM_RANKS_TTL, max_size=500)
    _user_rank_cache: TTLCache = TTLCache(ttl=PERM_USER_RANK_TTL, max_size=5000)

    def __init__(
        self,
        db: DatabaseService | None = None,
        cache_backend: AsyncCacheBackendProtocol | None = None,
    ) -> None:
        """Initialize the permission assignment controller.

        Parameters
        ----------
        db : DatabaseService | None, optional
            The database service instance. If None, uses the default service.
        cache_backend : AsyncCacheBackendProtocol | None, optional
            Optional cache backend (Valkey/in-memory) for assignments and user rank.
        """
        super().__init__(PermissionAssignment, db)
        self._backend = cache_backend

    async def assign_permission_rank(
        self,
        permission_rank_id: int,
        role_id: int,
    ) -> PermissionAssignment:
        """Assign a permission level to a role.

        Returns
        -------
        PermissionAssignment
            The newly created permission assignment.
        """
        result = await self.create(
            permission_rank_id=permission_rank_id,
            role_id=role_id,
        )
        if self._backend is not None:
            await self._backend.delete(f"{PERM_KEY_PREFIX}permission_assignments")
        else:
            self._assignments_cache.invalidate("permission_assignments")
        logger.trace("Invalidated permission assignment cache")
        return result

    async def get_all_assignments(self) -> list[PermissionAssignment]:
        """Get all permission assignments.

        Returns
        -------
        list[PermissionAssignment]
            List of all permission assignments.
        """
        cache_key = f"{PERM_KEY_PREFIX}permission_assignments"
        if self._backend is not None:
            raw = await self._backend.get(cache_key)
            if raw is not None and isinstance(raw, list):
                logger.trace("Cache hit for permission assignments")
                items = cast(list[dict[str, Any]], raw)
                return [PermissionAssignment.model_validate(d) for d in items]
            if raw is not None:
                logger.warning(
                    "Malformed cache entry for permission assignments, fetching from DB",
                )
        if self._backend is None:
            cached = self._assignments_cache.get("permission_assignments")
            if cached is not None:
                logger.trace("Cache hit for permission assignments")
                return cached

        result = await self.find_all()
        if self._backend is not None:
            await self._backend.set(
                cache_key,
                [m.model_dump() for m in result],
                ttl_sec=PERM_RANKS_TTL,
            )
        else:
            self._assignments_cache.set("permission_assignments", result)
        logger.trace("Cached permission assignments")
        return result

    async def remove_role_assignment(self, role_id: int) -> bool:
        """Remove a permission level assignment from a role.

        Returns
        -------
        bool
            True if removed successfully, False otherwise.
        """
        deleted_count = await self.delete_where(
            filters=PermissionAssignment.role_id == role_id,
        )
        if deleted_count > 0:
            if self._backend is not None:
                await self._backend.delete(f"{PERM_KEY_PREFIX}permission_assignments")
            else:
                self._assignments_cache.invalidate("permission_assignments")
            logger.trace("Invalidated permission assignment cache")
        return deleted_count > 0

    async def remove_role_assignments_from_rank(
        self,
        permission_rank_id: int,
        role_ids: list[int],
    ) -> int:
        """Remove permission level assignments for multiple roles from a single rank.

        Only deletes assignments for the given permission_rank_id, so roles are
        removed from that rank only, not from every rank.

        Invalidates the permission assignments cache once after all deletions.

        Returns
        -------
        int
            Number of role assignments removed.
        """
        if not role_ids:
            return 0
        deleted_count = await self.delete_where(
            filters=(PermissionAssignment.permission_rank_id == permission_rank_id)
            & (PermissionAssignment.role_id.in_(role_ids)),  # type: ignore[attr-defined]
        )
        if deleted_count > 0:
            if self._backend is not None:
                await self._backend.delete(f"{PERM_KEY_PREFIX}permission_assignments")
            else:
                self._assignments_cache.invalidate("permission_assignments")
            logger.trace("Invalidated permission assignment cache")
        return deleted_count

    async def get_user_permission_rank(  # noqa: PLR0911, PLR0912
        self,
        user_id: int,
        user_roles: list[int],
    ) -> int:
        """Get the highest permission rank a user has based on their roles.

        Parameters
        ----------
        user_id : int
            The user ID.
        user_roles : list[int]
            List of role IDs the user has.

        Returns
        -------
        int
            The highest permission rank (0 if user has no assigned roles).
        """
        if not user_roles:
            return 0

        sorted_roles = tuple(sorted(user_roles))
        cache_key = f"{PERM_KEY_PREFIX}user_permission_rank:{user_id}:{sorted_roles}"
        if self._backend is not None:
            raw = await self._backend.get(cache_key)
            if raw is not None and isinstance(raw, int):
                logger.trace(
                    f"Cache hit for user permission rank (user {user_id})",
                )
                return raw
        else:
            cached = self._user_rank_cache.get(cache_key)
            if cached is not None:
                logger.trace(
                    f"Cache hit for user permission rank (user {user_id})",
                )
                return cached

        # Get all permission assignments (uses cache)
        assignments = await self.get_all_assignments()
        if not assignments:
            if self._backend is not None:
                await self._backend.set(cache_key, 0, ttl_sec=PERM_USER_RANK_TTL)
            else:
                self._user_rank_cache.set(cache_key, 0)
            return 0

        max_rank = 0
        assigned_role_ids = {assignment.role_id for assignment in assignments}
        user_assigned_roles = set(user_roles) & assigned_role_ids
        if not user_assigned_roles:
            if self._backend is not None:
                await self._backend.set(cache_key, 0, ttl_sec=PERM_USER_RANK_TTL)
            else:
                self._user_rank_cache.set(cache_key, 0)
            return 0

        permission_rank_ids = {
            assignment.permission_rank_id
            for assignment in assignments
            if assignment.role_id in user_assigned_roles
        }
        if not permission_rank_ids:
            if self._backend is not None:
                await self._backend.set(cache_key, 0, ttl_sec=PERM_USER_RANK_TTL)
            else:
                self._user_rank_cache.set(cache_key, 0)
            return 0

        async with self.db.session() as session:
            stmt = (
                select(PermissionRank).where(PermissionRank.id.in_(permission_rank_ids))  # type: ignore[attr-defined]
            )
            result = await session.execute(stmt)
            rank_records = list(result.scalars().all())
            for rank_record in rank_records:
                session.expunge(rank_record)

        for rank_record in rank_records:
            if rank_record.rank > max_rank:
                max_rank = int(rank_record.rank)

        if self._backend is not None:
            await self._backend.set(
                cache_key,
                max_rank,
                ttl_sec=PERM_USER_RANK_TTL,
            )
        else:
            self._user_rank_cache.set(cache_key, max_rank)
        logger.trace(f"Cached user permission rank {max_rank} for user {user_id}")
        return max_rank


def wrap_optional_perm(value: PermissionCommand | None) -> dict[str, Any]:
    """Wrap optional PermissionCommand for backend (distinguish cached None from miss)."""
    return {"_v": value.model_dump() if value is not None else None}


def unwrap_optional_perm(raw: Any) -> PermissionCommand | None:
    """Unwrap optional PermissionCommand from backend."""
    if raw is None or not isinstance(raw, dict):
        return None
    raw_dict = cast(dict[str, Any], raw)
    v = raw_dict.get("_v")
    if v is None:
        return None
    return PermissionCommand.model_validate(v)


class PermissionCommandController(BaseController[PermissionCommand]):
    """Controller for managing command permission requirements."""

    # Shared cache when no backend
    _command_permissions_cache: TTLCache = TTLCache(ttl=PERM_RANKS_TTL, max_size=2000)

    def __init__(
        self,
        db: DatabaseService | None = None,
        cache_backend: AsyncCacheBackendProtocol | None = None,
    ) -> None:
        """Initialize the command permission controller.

        Parameters
        ----------
        db : DatabaseService | None, optional
            The database service instance. If None, uses the default service.
        cache_backend : AsyncCacheBackendProtocol | None, optional
            Optional cache backend (Valkey/in-memory) for command permissions.
        """
        super().__init__(PermissionCommand, db)
        self._backend = cache_backend

    async def set_command_permission(
        self,
        command_name: str,
        required_rank: int,
        description: str | None = None,
    ) -> PermissionCommand:
        """Set the permission rank required for a command.

        Returns
        -------
        PermissionCommand
            The command permission record (created or updated).
        """
        result = await self.upsert(
            filters={"command_name": command_name},
            command_name=command_name,
            required_rank=required_rank,
            description=description,
        )
        if self._backend is not None:
            await self._backend.delete(
                f"{PERM_KEY_PREFIX}command_permission:{command_name}",
            )
            parts = command_name.split()
            for i in range(len(parts) - 1, 0, -1):
                parent_name = " ".join(parts[:i])
                await self._backend.delete(
                    f"{PERM_KEY_PREFIX}command_permission:{parent_name}",
                )
        else:
            cache_key = f"command_permission:{command_name}"
            self._command_permissions_cache.invalidate(cache_key)
            parts = command_name.split()
            for i in range(len(parts) - 1, 0, -1):
                parent_name = " ".join(parts[:i])
                parent_cache_key = f"command_permission:{parent_name}"
                self._command_permissions_cache.invalidate(parent_cache_key)
        logger.trace(f"Invalidated command permission cache for {command_name}")
        return result[0]  # upsert returns (record, created)

    async def invalidate_command_permission(self, command_name: str) -> None:
        """Invalidate the command permission cache for a command and its parents.

        Call after removing a command permission (e.g. delete_where) so the next
        get_command_permission sees fresh data.

        Notes
        -----
        This invalidates only the controller cache (PERM_KEY_PREFIX). Callers that
        use PermissionSystem.get_command_permission must also call
        PermissionSystem.invalidate_command_permission_cache so the fallback cache
        (PERM_FALLBACK_KEY_PREFIX) is cleared; both layers must be invalidated
        together after a database change.
        """
        if self._backend is not None:
            await self._backend.delete(
                f"{PERM_KEY_PREFIX}command_permission:{command_name}",
            )
            parts = command_name.split()
            for i in range(len(parts) - 1, 0, -1):
                parent_name = " ".join(parts[:i])
                await self._backend.delete(
                    f"{PERM_KEY_PREFIX}command_permission:{parent_name}",
                )
        else:
            cache_key = f"command_permission:{command_name}"
            self._command_permissions_cache.invalidate(cache_key)
            parts = command_name.split()
            for i in range(len(parts) - 1, 0, -1):
                parent_name = " ".join(parts[:i])
                parent_cache_key = f"command_permission:{parent_name}"
                self._command_permissions_cache.invalidate(parent_cache_key)
        logger.trace(f"Invalidated command permission cache for {command_name}")

    async def get_command_permission(
        self,
        command_name: str,
    ) -> PermissionCommand | None:
        """Get the permission requirement for a specific command.

        Returns
        -------
        PermissionCommand | None
            The command permission record if found, None otherwise.
        """
        cache_key = f"{PERM_KEY_PREFIX}command_permission:{command_name}"
        if self._backend is not None:
            raw = await self._backend.get(cache_key)
            if raw is not None:
                logger.trace(f"Cache hit for command permission {command_name}")
                return unwrap_optional_perm(raw)
        else:
            cached = self._command_permissions_cache.get(
                f"command_permission:{command_name}",
            )
            if cached is not None:
                logger.trace(f"Cache hit for command permission {command_name}")
                return unwrap_optional_perm(cached)

        result = await self.find_one(
            filters=PermissionCommand.command_name == command_name,
        )
        wrapped = wrap_optional_perm(result)
        if self._backend is not None:
            await self._backend.set(
                cache_key,
                wrapped,
                ttl_sec=PERM_RANKS_TTL,
            )
        else:
            self._command_permissions_cache.set(
                f"command_permission:{command_name}", wrapped,
            )
        logger.trace(f"Cached command permission for {command_name}")
        return result

    async def get_all_command_permissions(self) -> list[PermissionCommand]:
        """Get all command permissions.

        Returns
        -------
        list[PermissionCommand]
            List of all command permissions ordered by name.
        """
        return await self.find_all(order_by=PermissionCommand.command_name)
