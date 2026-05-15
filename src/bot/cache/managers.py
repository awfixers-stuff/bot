"""Cache managers for jail status (in-memory or backend)."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from typing import Any

from loguru import logger

from bot.cache.backend import AsyncCacheBackend
from bot.cache.ttl import TTLCache

# Invalidated on jail/unjail; TTL only for cold expiry.
JAIL_STATUS_TTL_SEC = 3600.0  # 1 hour

__all__ = ["JailStatusCache"]


class JailStatusCache:
    """
    Cache manager for jail status checks.

    Provides a singleton instance that caches jail status per (guild_id, user_id)
    tuple. Supports optional AsyncCacheBackend (e.g. Valkey).
    """

    __slots__ = ("_backend", "_cache", "_locks", "_locks_lock")
    _instance: JailStatusCache | None = None
    _cache: TTLCache
    _locks: dict[tuple[int, int], asyncio.Lock]
    _locks_lock: asyncio.Lock
    _backend: AsyncCacheBackend | None

    def __new__(cls) -> JailStatusCache:
        """Create or return the singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._cache = TTLCache(ttl=JAIL_STATUS_TTL_SEC, max_size=5000)
            cls._instance._locks = {}
            cls._instance._locks_lock = asyncio.Lock()
            cls._instance._backend = None
        return cls._instance

    def set_backend(self, backend: AsyncCacheBackend) -> None:
        """Set the cache backend.

        Parameters
        ----------
        backend : AsyncCacheBackend
            Backend instance to use for cache operations.
        """
        self._backend = backend
        logger.debug(
            "JailStatusCache backend set to {}",
            type(backend).__name__,
        )

    def _get_lock_key(self, guild_id: int, user_id: int) -> tuple[int, int]:
        """Generate lock key for guild_id and user_id."""
        return (guild_id, user_id)

    async def _get_lock(self, guild_id: int, user_id: int) -> asyncio.Lock:
        """Get or create a lock for a specific (guild_id, user_id) pair."""
        lock_key = self._get_lock_key(guild_id, user_id)
        async with self._locks_lock:
            if lock_key not in self._locks:
                self._locks[lock_key] = asyncio.Lock()
        return self._locks[lock_key]

    def _cache_key(self, guild_id: int, user_id: int) -> str:
        """Return the cache key (backend adds bot: prefix)."""
        return f"jail_status:{guild_id}:{user_id}"

    async def get(self, guild_id: int, user_id: int) -> bool | None:
        """
        Get cached jail status for a user.

        Returns
        -------
        bool | None
            True if jailed, False if not jailed, None if not cached.
        """
        key = self._cache_key(guild_id, user_id)
        if self._backend is not None:
            value = await self._backend.get(key)
            if value is None:
                return None
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value in ("1", "true", "True")
            return bool(value)
        return self._cache.get(key)

    async def set(self, guild_id: int, user_id: int, is_jailed: bool) -> None:
        """Cache jail status for a user.

        Parameters
        ----------
        guild_id : int
            The guild ID.
        user_id : int
            The user ID.
        is_jailed : bool
            Whether the user is jailed.
        """
        key = self._cache_key(guild_id, user_id)
        if self._backend is not None:
            await self._backend.set(key, is_jailed, ttl_sec=JAIL_STATUS_TTL_SEC)
        else:
            self._cache.set(key, is_jailed)

    async def get_or_fetch(
        self,
        guild_id: int,
        user_id: int,
        fetch_func: Callable[[], Coroutine[Any, Any, bool]],
    ) -> bool:
        """Get cached value or fetch and cache with async locking (stampede protection).

        Parameters
        ----------
        guild_id : int
            The guild ID.
        user_id : int
            The user ID.
        fetch_func : Callable[[], Coroutine[Any, Any, bool]]
            Async callable that returns the jail status when cache misses.

        Returns
        -------
        bool
            Cached or freshly fetched jail status.
        """
        cached_status = await self.get(guild_id, user_id)
        if cached_status is not None:
            return cached_status

        lock = await self._get_lock(guild_id, user_id)
        async with lock:
            cached_status = await self.get(guild_id, user_id)
            if cached_status is not None:
                return cached_status
            is_jailed = await fetch_func()
            await self.set(guild_id, user_id, is_jailed)
            return is_jailed

    async def async_set(self, guild_id: int, user_id: int, is_jailed: bool) -> None:
        """Cache jail status with async locking; overwrites any existing value.

        Parameters
        ----------
        guild_id : int
            The guild ID.
        user_id : int
            The user ID.
        is_jailed : bool
            Whether the user is jailed.
        """
        key = self._cache_key(guild_id, user_id)
        lock = await self._get_lock(guild_id, user_id)
        async with lock:
            if self._backend is not None:
                await self._backend.set(key, is_jailed, ttl_sec=JAIL_STATUS_TTL_SEC)
            else:
                self._cache.set(key, is_jailed)

    async def invalidate(self, guild_id: int, user_id: int) -> None:
        """Invalidate cached jail status for a user.

        Parameters
        ----------
        guild_id : int
            The guild ID.
        user_id : int
            The user ID.
        """
        key = self._cache_key(guild_id, user_id)
        if self._backend is not None:
            await self._backend.delete(key)
        else:
            self._cache.invalidate(key)
        logger.debug(
            "Invalidated jail status cache for guild {}, user {}",
            guild_id,
            user_id,
        )

    async def invalidate_guild(self, guild_id: int) -> None:
        """Invalidate in-memory jail status entries for a guild.

        Parameters
        ----------
        guild_id : int
            The guild ID to invalidate.

        Notes
        -----
        Only the in-memory cache is cleared for this guild; when a backend
        (e.g. Valkey) is configured, backend keys for this guild are not
        deleted. For full clear use :meth:`clear_all` (in-memory only).
        """
        prefix = f"jail_status:{guild_id}:"
        removed = self._cache.invalidate_keys_matching(
            lambda key: str(key).startswith(prefix),
        )
        logger.debug(
            "Invalidated {} jail status cache entries for guild {}",
            removed,
            guild_id,
        )

    async def clear_all(self) -> None:
        """Clear all cached jail status entries (in-memory only).

        Notes
        -----
        When a backend is configured, backend keys are not deleted.
        """
        self._cache.clear()
        logger.debug("Cleared all jail status cache entries")
