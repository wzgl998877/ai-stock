"""Redis 异步搜索缓存 — 防击穿 + 自动降级"""

import json
import logging
from typing import Optional

import redis.asyncio as aioredis

from app.core.config import settings
from app.domain.value_objects.search_result import SearchResponse

logger = logging.getLogger(__name__)


class SearchCache:
    """基于 Redis 的异步搜索缓存。

    - Redis 不可用时自动降级为 no-op，不影响搜索功能
    - 使用 SETNX 实现防击穿（分布式锁）
    """

    KEY_PREFIX = "search:result:"
    LOCK_PREFIX = "search:lock:"
    DEFAULT_TTL = 600  # 10 分钟
    LOCK_TTL = 30  # 锁等待超时 30 秒
    LOCK_WAIT_INTERVAL = 0.2  # 轮询间隔

    def __init__(self) -> None:
        self._client: Optional[aioredis.Redis] = None
        self._available: bool = True

    async def _ensure_client(self) -> Optional[aioredis.Redis]:
        if self._client is not None:
            return self._client
        try:
            self._client = aioredis.Redis.from_url(
                settings.redis_url,
                decode_responses=True,
            )
            await self._client.ping()
        except Exception:
            logger.warning("搜索缓存 Redis 连接失败，缓存将禁用")
            self._available = False
            self._client = None
        return self._client

    async def get(self, cache_key: str) -> Optional[SearchResponse]:
        """读取缓存，未命中或不可用时返回 None。"""
        if not self._available:
            return None
        client = await self._ensure_client()
        if client is None:
            return None
        try:
            raw = await client.get(f"{self.KEY_PREFIX}{cache_key}")
            if raw is None:
                return None
            return SearchResponse.from_dict(json.loads(raw))
        except Exception:
            logger.exception("搜索缓存读取失败: %s", cache_key)
            return None

    async def set(self, cache_key: str, response: SearchResponse, ttl: int = 0) -> None:
        """写入缓存。"""
        if not self._available:
            return
        client = await self._ensure_client()
        if client is None:
            return
        try:
            payload = json.dumps(response.to_dict(), ensure_ascii=False)
            effective_ttl = ttl or self.DEFAULT_TTL
            await client.set(f"{self.KEY_PREFIX}{cache_key}", payload, ex=effective_ttl)
        except Exception:
            logger.exception("搜索缓存写入失败: %s", cache_key)

    async def acquire_lock(self, cache_key: str) -> bool:
        """获取缓存填充锁（防击穿）。成功返回 True。"""
        if not self._available:
            return True  # Redis 不可用时直接放行
        client = await self._ensure_client()
        if client is None:
            return True
        try:
            return bool(
                await client.set(
                    f"{self.LOCK_PREFIX}{cache_key}",
                    "1",
                    nx=True,
                    ex=self.LOCK_TTL,
                )
            )
        except Exception:
            return True  # 出错放行

    async def release_lock(self, cache_key: str) -> None:
        """释放缓存填充锁。"""
        if not self._available:
            return
        client = await self._ensure_client()
        if client is None:
            return
        try:
            await client.delete(f"{self.LOCK_PREFIX}{cache_key}")
        except Exception:
            pass

    async def wait_for_fill(self, cache_key: str, timeout: float = 10.0) -> Optional[SearchResponse]:
        """等待其他协程填充缓存，超时返回 None。"""
        import asyncio

        deadline = asyncio.get_event_loop().time() + timeout
        while asyncio.get_event_loop().time() < deadline:
            # 先检查缓存是否已填充
            result = await self.get(cache_key)
            if result is not None:
                return result
            # 检查锁是否还存在
            client = await self._ensure_client()
            if client is not None:
                try:
                    exists = await client.exists(f"{self.LOCK_PREFIX}{cache_key}")
                    if not exists:
                        # 锁已释放但缓存仍为空 => 填充失败
                        return None
                except Exception:
                    return None
            await asyncio.sleep(self.LOCK_WAIT_INTERVAL)
        return None

    async def close(self) -> None:
        if self._client is not None:
            try:
                await self._client.aclose()
            except Exception:
                pass
            self._client = None
