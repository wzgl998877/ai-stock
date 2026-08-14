"""iLink context_token 与长轮询游标的双级存储。

内存 dict（L1）+ Redis（L2）写穿透、读回填：

- **context_token**（协议核心：回复必须携带用户最近一条入站消息的 token）按
  ``user_id`` 缓存，TTL 7 天。token 生命周期协议未明示，过期比不过期安全——
  读到失效 token 只会导致一次 ret=-2，下次入站消息会刷新；
- **游标 get_updates_buf** 无 TTL（单调演进）。跨重启持久化后长轮询可从断点
  继续；丢失最多重放一批消息（handler 只记日志，无害）。

Redis 挂掉时自动降级为纯内存（复用 ``redis_cache`` 单例的降级哲学）。
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from app.infrastructure.cache.redis_cache import RedisCache, redis_cache

logger = logging.getLogger(__name__)

_TOKEN_TTL = 7 * 24 * 3600  # context_token 缓存 7 天
_CURSOR_KEY = "wechat:ilink:get_updates_buf"


def _token_key(user_id: str) -> str:
    return f"wechat:ilink:context_token:{user_id}"


class ILinkTokenStore:
    """context_token + 长轮询游标存储（内存 + Redis 写穿透）。"""

    def __init__(self, redis: Optional[RedisCache] = None):
        # 默认注入全局单例；测试可换 Fake
        self._redis = redis if redis is not None else redis_cache
        self._tokens: dict[str, str] = {}
        self._cursor: Optional[str] = None
        self._lock = asyncio.Lock()

    async def get_context_token(self, user_id: str) -> Optional[str]:
        """L1 命中直接返回；未命中查 Redis 回填内存。"""
        async with self._lock:
            tok = self._tokens.get(user_id)
            if tok:
                return tok
            try:
                tok = await self._redis.get(_token_key(user_id))
            except Exception:
                logger.warning("读取 context_token 失败（Redis 异常，忽略）", exc_info=True)
                return None
            if tok:
                self._tokens[user_id] = tok
            return tok or None

    async def set_context_token(self, user_id: str, token: str) -> None:
        async with self._lock:
            self._tokens[user_id] = token
            try:
                await self._redis.set(_token_key(user_id), token, ttl=_TOKEN_TTL)
            except Exception:
                logger.warning("持久化 context_token 失败（Redis 异常，忽略）", exc_info=True)

    async def get_cursor(self) -> str:
        """当前游标；从未持久化时返回空字符串（服务器会从头推）。"""
        async with self._lock:
            if self._cursor is not None:
                return self._cursor
            try:
                buf = await self._redis.get(_CURSOR_KEY)
            except Exception:
                logger.warning("读取长轮询游标失败（Redis 异常，忽略）", exc_info=True)
                return ""
            self._cursor = buf if isinstance(buf, str) else ""
            return self._cursor

    async def set_cursor(self, buf: str) -> None:
        async with self._lock:
            self._cursor = buf
            try:
                await self._redis.set(_CURSOR_KEY, buf)
            except Exception:
                logger.warning("持久化长轮询游标失败（Redis 异常，忽略）", exc_info=True)
