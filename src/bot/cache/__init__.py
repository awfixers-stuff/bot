"""Cache layer with optional Valkey (Redis-compatible) backend.

Provides CacheService, backends (InMemoryBackend, ValkeyBackend), TTL cache,
and cache managers (JailStatusCache).
"""

from bot.cache.backend import (
    AsyncCacheBackend,
    InMemoryBackend,
    ValkeyBackend,
    get_cache_backend,
)
from bot.cache.managers import JailStatusCache
from bot.cache.service import CacheService
from bot.cache.ttl import TTLCache

# Alias for code that still uses the old protocol name
AsyncCacheBackendProtocol = AsyncCacheBackend

__all__ = [
    "AsyncCacheBackend",
    "AsyncCacheBackendProtocol",
    "CacheService",
    "InMemoryBackend",
    "JailStatusCache",
    "TTLCache",
    "ValkeyBackend",
    "get_cache_backend",
]
