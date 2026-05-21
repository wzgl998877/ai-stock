"""分时数据多源聚合客户端。

按优先级 fallback:
1. Redis 缓存
2. 腾讯财经（主）
3. 新浪财经（备）
4. TwelveData（增强）
"""

import logging
from typing import List, Dict

from app.core.config import settings
from app.infrastructure.cache.redis_cache import redis_cache
from app.infrastructure.market.tencent_client import TencentMinuteClient
from app.infrastructure.market.sina_client import SinaMinuteClient
from app.infrastructure.market.twelvedata_client import TwelveDataMinuteClient

logger = logging.getLogger(__name__)


class MinuteClient:
    """分时数据多源聚合入口。"""

    def __init__(self) -> None:
        self._tencent = TencentMinuteClient()
        self._sina = SinaMinuteClient()
        self._twelvedata = TwelveDataMinuteClient()

    async def get_minute_data(self, code: str) -> List[Dict]:
        """获取分时数据，带缓存和多源 fallback。"""
        cache_key = f"stock:minute:{code}"

        # 1. 查 Redis 缓存
        cached = await redis_cache.get(cache_key)
        if cached:
            logger.info("分时数据缓存命中: %s", code)
            return cached

        # 2. 按序尝试各数据源
        sources = [
            ("tencent", self._tencent),
            ("sina", self._sina),
            ("twelvedata", self._twelvedata),
        ]

        for name, client in sources:
            try:
                data = await client.fetch(code)
                if data:
                    logger.info("分时数据来源: %s (%d 条)", name, len(data))
                    # 写入缓存（空数据不缓存）
                    await redis_cache.set(cache_key, data, ttl=settings.minute_cache_ttl)
                    return data
            except Exception as exc:
                logger.warning("分时数据源 %s 获取失败: %s", name, exc)

        # 全部失败返回空列表，不抛异常
        logger.warning("所有分时数据源均失败: %s", code)
        return []
