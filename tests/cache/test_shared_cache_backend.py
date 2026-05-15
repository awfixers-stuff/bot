"""Unit tests for JailStatusCache with backend set."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock

import pytest

from bot.cache import JailStatusCache
from bot.cache.backend import InMemoryBackend


@pytest.mark.unit
class TestJailStatusCacheWithBackend:
    """JailStatusCache get/set/invalidate when backend is set."""

    @pytest.fixture
    def backend(self) -> InMemoryBackend:
        """Fresh in-memory backend per test."""
        return InMemoryBackend()

    @pytest.fixture
    def cache(self, backend: InMemoryBackend) -> Generator[JailStatusCache]:
        """Singleton with backend set; teardown clears state to avoid leakage."""
        jail_cache = JailStatusCache()
        jail_cache.set_backend(backend)
        yield jail_cache
        jail_cache._backend = None
        jail_cache._cache.clear()
        jail_cache._locks.clear()

    @pytest.mark.asyncio
    async def test_get_returns_none_when_not_cached(
        self,
        cache: JailStatusCache,
    ) -> None:
        """Get with uncached (guild, user) returns None."""
        assert await cache.get(1, 2) is None

    @pytest.mark.asyncio
    async def test_set_and_get_roundtrip(self, cache: JailStatusCache) -> None:
        """Set then get returns the same jail status."""
        await cache.set(10, 20, is_jailed=True)
        assert await cache.get(10, 20) is True
        await cache.set(10, 21, is_jailed=False)
        assert await cache.get(10, 21) is False

    @pytest.mark.asyncio
    async def test_invalidate_removes_entry(self, cache: JailStatusCache) -> None:
        """Invalidate removes the entry; get returns None."""
        await cache.set(5, 6, is_jailed=True)
        await cache.invalidate(5, 6)
        assert await cache.get(5, 6) is None

    @pytest.mark.asyncio
    async def test_get_or_fetch_uses_backend(self, cache: JailStatusCache) -> None:
        """get_or_fetch caches via backend and returns fetched value."""

        async def fetch() -> bool:
            return True

        result = await cache.get_or_fetch(7, 8, fetch)
        assert result is True
        assert await cache.get(7, 8) is True

    @pytest.mark.asyncio
    async def test_get_returns_bool_when_backend_returns_string(
        self,
        cache: JailStatusCache,
        backend: InMemoryBackend,
    ) -> None:
        """Get when backend returns string 'true' or '1' is normalized to bool."""
        backend.get = AsyncMock(return_value="true")
        assert await cache.get(1, 2) is True
        backend.get = AsyncMock(return_value="1")
        assert await cache.get(1, 3) is True
        backend.get = AsyncMock(return_value="false")
        assert await cache.get(1, 4) is False

    @pytest.mark.asyncio
    async def test_async_set_overwrites_when_backend_has_value(
        self,
        cache: JailStatusCache,
        backend: InMemoryBackend,
    ) -> None:
        """async_set overwrites existing value (same as set)."""
        backend.get = AsyncMock(return_value=True)
        backend.set = AsyncMock()
        await cache.async_set(10, 20, is_jailed=False)
        backend.set.assert_called_once()
        call_args = backend.set.call_args
        assert call_args[0][1] is False  # is_jailed

    @pytest.mark.asyncio
    async def test_async_set_writes_when_backend_missing(
        self,
        cache: JailStatusCache,
        backend: InMemoryBackend,
    ) -> None:
        """async_set when backend has no value writes."""
        await cache.async_set(11, 22, is_jailed=True)
        assert await cache.get(11, 22) is True

    @pytest.mark.asyncio
    async def test_invalidate_guild_removes_matching_keys(
        self,
        cache: JailStatusCache,
    ) -> None:
        """invalidate_guild removes in-memory entries for that guild (in-memory only)."""
        cache._backend = None  # Use in-memory path so _cache is populated
        await cache.set(100, 1, True)
        await cache.set(100, 2, False)
        await cache.set(101, 1, True)
        await cache.invalidate_guild(100)
        assert await cache.get(100, 1) is None
        assert await cache.get(100, 2) is None
        assert await cache.get(101, 1) is True

    @pytest.mark.asyncio
    async def test_clear_all_clears_entries(self, cache: JailStatusCache) -> None:
        """clear_all clears in-memory cache (when backend is None, get then returns None)."""
        cache._backend = None
        await cache.set(5, 6, is_jailed=True)
        await cache.clear_all()
        assert await cache.get(5, 6) is None
