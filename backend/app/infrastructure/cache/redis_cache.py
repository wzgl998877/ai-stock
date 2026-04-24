"""Redis cache wrapper with auto-degradation on connection failure."""

import json
import logging
from typing import Any, Optional

import redis

from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisCache:
    """Singleton Redis cache that auto-degrades when Redis is unavailable.

    On the first operation, attempts to connect. If the connection fails,
    sets an internal `_available` flag to False and silently skips all
    subsequent operations (get returns None, set/delete are no-ops).
    """

    def __init__(self) -> None:
        self._available: bool = True
        self._client: Optional[redis.Redis] = None

    def _ensure_client(self) -> Optional[redis.Redis]:
        """Lazily initialise the Redis client. Returns None on failure."""
        if self._client is not None:
            return self._client
        try:
            self._client = redis.Redis.from_url(
                settings.redis_url,
                decode_responses=True,
            )
            # Verify connectivity with a quick ping
            self._client.ping()
        except Exception:
            logger.warning("Redis connection failed, cache will be disabled")
            self._available = False
            self._client = None
        return self._client

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, key: str) -> Optional[Any]:
        """Get a value by key. Returns deserialized Python object or None."""
        if not self._available:
            return None
        client = self._ensure_client()
        if client is None:
            return None
        try:
            raw = client.get(key)
            if raw is None:
                return None
            return json.loads(raw)
        except Exception:
            logger.exception("Redis get failed for key: %s", key)
            self._available = False
            return None

    def set(self, key: str, value: Any, ttl: int = 0) -> None:
        """Store a value as JSON string with optional TTL (seconds)."""
        if not self._available:
            return
        client = self._ensure_client()
        if client is None:
            return
        try:
            client.set(key, json.dumps(value, ensure_ascii=False), ex=ttl or None)
        except Exception:
            logger.exception("Redis set failed for key: %s", key)
            self._available = False

    def delete(self, key: str) -> None:
        """Delete a key. Silently skips if Redis is unavailable."""
        if not self._available:
            return
        client = self._ensure_client()
        if client is None:
            return
        try:
            client.delete(key)
        except Exception:
            logger.exception("Redis delete failed for key: %s", key)
            self._available = False

    def exists(self, key: str) -> bool:
        """Check if a key exists. Returns False if Redis is unavailable."""
        if not self._available:
            return False
        client = self._ensure_client()
        if client is None:
            return False
        try:
            return bool(client.exists(key))
        except Exception:
            logger.exception("Redis exists failed for key: %s", key)
            self._available = False
            return False


# Module-level singleton instance
redis_cache = RedisCache()
