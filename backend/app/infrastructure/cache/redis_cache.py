"""Async Redis cache wrapper with auto-degradation on connection failure."""

import json
import logging
from typing import Any, Optional

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisCache:
    """Async Redis cache that auto-degrades when Redis is unavailable.

    On the first operation, attempts to connect. If the connection fails,
    sets an internal `_available` flag to False and silently skips all
    subsequent operations (get returns None, set/delete are no-ops).
    """

    def __init__(self) -> None:
        self._available: bool = True
        self._client: Optional[aioredis.Redis] = None

    async def _ensure_client(self) -> Optional[aioredis.Redis]:
        """Lazily initialise the Redis client. Returns None on failure."""
        if self._client is not None:
            return self._client
        try:
            self._client = aioredis.Redis.from_url(
                settings.redis_url,
                decode_responses=True,
            )
            await self._client.ping()
        except Exception:
            logger.warning("Redis connection failed, cache will be disabled")
            self._available = False
            self._client = None
        return self._client

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get(self, key: str) -> Optional[Any]:
        """Get a value by key. Returns deserialized Python object or None."""
        if not self._available:
            return None
        client = await self._ensure_client()
        if client is None:
            return None
        try:
            raw = await client.get(key)
            if raw is None:
                return None
            return json.loads(raw)
        except Exception:
            logger.exception("Redis get failed for key: %s", key)
            self._available = False
            return None

    async def set(self, key: str, value: Any, ttl: int = 0) -> None:
        """Store a value as JSON string with optional TTL (seconds)."""
        if not self._available:
            return
        client = await self._ensure_client()
        if client is None:
            return
        try:
            await client.set(key, json.dumps(value, ensure_ascii=False), ex=ttl or None)
        except Exception:
            logger.exception("Redis set failed for key: %s", key)
            self._available = False

    async def delete(self, key: str) -> None:
        """Delete a key. Silently skips if Redis is unavailable."""
        if not self._available:
            return
        client = await self._ensure_client()
        if client is None:
            return
        try:
            await client.delete(key)
        except Exception:
            logger.exception("Redis delete failed for key: %s", key)
            self._available = False

    async def exists(self, key: str) -> bool:
        """Check if a key exists. Returns False if Redis is unavailable."""
        if not self._available:
            return False
        client = await self._ensure_client()
        if client is None:
            return False
        try:
            return bool(await client.exists(key))
        except Exception:
            logger.exception("Redis exists failed for key: %s", key)
            self._available = False
            return False

    async def scan(self, cursor: int = 0, match: str = None, count: int = 100) -> tuple[int, list[str]]:
        """Scan keys matching a pattern."""
        if not self._available:
            return 0, []
        client = await self._ensure_client()
        if client is None:
            return 0, []
        try:
            return await client.scan(cursor, match=match, count=count)
        except Exception:
            logger.exception("Redis scan failed")
            self._available = False
            return 0, []


# Module-level singleton instance
redis_cache = RedisCache()
