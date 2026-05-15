"""
Prefix management with in-memory caching for optimal performance.

This module provides efficient prefix resolution for Discord commands by maintaining
an in-memory cache of guild prefixes, eliminating repeated lookups on every message.

The PrefixManager uses a cache-first approach:

1. Check environment variable override (BOT_INFO__PREFIX)
2. Check in-memory cache (O(1) lookup)
3. Load from Valkey backend on cache miss
4. Persist changes asynchronously to avoid blocking

Note: Guild/GuildConfig models have been removed (single-guild simplification).
Prefix persistence uses the cache backend (Valkey) instead of the database.
On restart without Valkey, custom prefixes are not persisted and the default is used.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from loguru import logger

from bot.cache import get_cache_backend
from bot.shared.config import CONFIG

if TYPE_CHECKING:
    from bot.core.bot import Bot

__all__ = ["PrefixManager"]


class PrefixManager:
    """
    Manages command prefixes with in-memory caching.

    Provides O(1) prefix lookups after initial cache load through lazy loading
    and automatic caching. See module docstring for resolution priority order.

    Attributes
    ----------
    bot : Bot
        The bot instance this manager is attached to.
    _prefix_cache : dict[int, str]
        In-memory cache mapping guild IDs to prefixes.
    _cache_loaded : bool
        Whether the initial cache load has completed.
    _default_prefix : str
        Default prefix from configuration.
    _loading_lock : asyncio.Lock
        Lock to prevent concurrent cache loading.
    """

    def __init__(self, bot: Bot) -> None:
        """
        Initialize the prefix manager.

        Parameters
        ----------
        bot : Bot
            The bot instance to manage prefixes for.
        """
        self.bot = bot
        self._prefix_cache: dict[int, str] = {}
        self._cache_loaded = False
        self._default_prefix = CONFIG.get_prefix()
        self._loading_lock = asyncio.Lock()

        logger.debug("PrefixManager initialized")

    async def get_prefix(self, guild_id: int | None) -> str:
        """
        Get the command prefix for a guild or DM.

        Follows the resolution priority documented in the module docstring.
        Automatically caches results for O(1) subsequent lookups.

        Parameters
        ----------
        guild_id : int | None
            The Discord guild ID, or None for DMs.

        Returns
        -------
        str
            The command prefix, or default prefix if not found.
        """
        if CONFIG.is_prefix_override_enabled():
            return self._default_prefix

        if guild_id is None:
            return self._default_prefix

        # Sync mirror for error extractor and fast path
        if guild_id in self._prefix_cache:
            return self._prefix_cache[guild_id]

        # Backend (Valkey or in-memory) when available
        backend = get_cache_backend(self.bot)
        key = f"prefix:{guild_id}"
        backend_val = await backend.get(key)
        if backend_val is not None and isinstance(backend_val, str):
            self._prefix_cache[guild_id] = backend_val
            return backend_val

        return await self._load_guild_prefix(guild_id)

    async def set_prefix(self, guild_id: int, prefix: str) -> None:
        """
        Set the command prefix for a guild.

        Updates cache immediately and persists to database asynchronously.
        No-op if prefix override is enabled via environment variable.

        Parameters
        ----------
        guild_id : int
            The Discord guild ID.
        prefix : str
            The new command prefix to set.
        """
        if CONFIG.is_prefix_override_enabled():
            logger.warning(
                f"Prefix override enabled - ignoring prefix change for guild {guild_id} to '{prefix}'. All guilds use default prefix '{self._default_prefix}'",
            )
            return

        self._prefix_cache[guild_id] = prefix

        # Write to backend when available (no TTL; prefix is long-lived)
        backend = get_cache_backend(self.bot)
        await backend.set(f"prefix:{guild_id}", prefix, ttl_sec=None)

        # Fire-and-forget: persist to database asynchronously
        asyncio.create_task(self._persist_prefix(guild_id, prefix))  # noqa: RUF006

        logger.info(f"Prefix updated for guild {guild_id}: '{prefix}'")

    async def _load_guild_prefix(self, guild_id: int) -> str:
        """
        Load a guild's prefix, falling back to default.

        In single-guild mode, Guild/GuildConfig models have been removed.
        Returns the default prefix from CONFIG. No database lookup is performed.

        Parameters
        ----------
        guild_id : int
            The Discord guild ID (unused, kept for API compatibility).

        Returns
        -------
        str
            The default prefix from configuration.
        """
        self._prefix_cache[guild_id] = self._default_prefix
        return self._default_prefix

    async def _persist_prefix(self, guild_id: int, prefix: str) -> None:
        """
        Persist a prefix change to the Valkey backend cache.

        Runs as a background task after set_prefix. In single-guild mode,
        Guild/GuildConfig models have been removed, so prefix is cached
        via the Valkey backend (not the database). Without Valkey, the
        prefix is kept only in memory.

        Parameters
        ----------
        guild_id : int
            The Discord guild ID.
        prefix : str
            The prefix to persist.
        """
        try:
            backend = get_cache_backend(self.bot)
            await backend.set(f"prefix:{guild_id}", prefix, ttl_sec=None)
            logger.debug(f"Prefix cached via backend for guild {guild_id}: '{prefix}'")
        except Exception as e:
            logger.error(
                f"Failed to cache prefix for guild {guild_id}: {type(e).__name__}",
            )
            # Remove from cache on failure to maintain consistency
            self._prefix_cache.pop(guild_id, None)

    async def load_all_prefixes(self) -> None:
        """
        Load the default prefix into cache.

        In single-guild mode, Guild/GuildConfig models have been removed.
        The default prefix from CONFIG is always available. No database
        lookup is performed. Idempotent and safe to call multiple times.
        """
        if self._cache_loaded:
            return

        async with self._loading_lock:
            if self._cache_loaded:
                return

            self._cache_loaded = True
            logger.debug(
                "Prefix cache loaded: default prefix is '{}'",
                self._default_prefix,
            )

    async def invalidate_cache(self, guild_id: int | None = None) -> None:
        """
        Invalidate prefix cache for a specific guild or all guilds.

        When guild_id is None, in-memory cache is cleared and backend keys for
        all cached guilds are removed (same as per-guild delete for each).
        When guild_id is set, both in-memory and backend state for that guild
        are invalidated.

        Parameters
        ----------
        guild_id : int | None, optional
            The guild ID to invalidate, or None to invalidate all.
            Defaults to None.

        Examples
        --------
        >>> await manager.invalidate_cache(123456789)  # Specific guild
        >>> await manager.invalidate_cache()  # All guilds (in-memory + backend)
        """
        backend = get_cache_backend(self.bot)
        if guild_id is None:
            keys_to_delete = list(self._prefix_cache.keys())
            if keys_to_delete:
                await asyncio.gather(
                    *(backend.delete(f"prefix:{gid}") for gid in keys_to_delete),
                )
            self._prefix_cache.clear()
            self._cache_loaded = False
            logger.debug("All prefix cache invalidated")
        else:
            await backend.delete(f"prefix:{guild_id}")
            self._prefix_cache.pop(guild_id, None)
            logger.debug(f"Prefix cache invalidated for guild {guild_id}")

    def get_cache_stats(self) -> dict[str, int]:
        """
        Get cache statistics for monitoring and debugging.

        Returns
        -------
        dict[str, int]
            Dictionary with keys:
            - cached_prefixes: Number of guilds in cache
            - cache_loaded: 1 if initial load completed, 0 otherwise
        """
        return {
            "cached_prefixes": len(self._prefix_cache),
            "cache_loaded": int(self._cache_loaded),
        }
