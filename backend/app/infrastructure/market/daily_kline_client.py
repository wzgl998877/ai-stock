"""K线数据多源聚合客户端。

按优先级 fallback:
1. 新浪财经（腾讯接口已失效，已移除）

不做缓存（Router 层已有 Redis 缓存），全失败返回空列表。
"""

import logging
from typing import Dict, List

from app.infrastructure.market.sina_kline_client import SinaKlineClient

logger = logging.getLogger(__name__)


class DailyKlineClient:
    """K线数据多源聚合入口。"""

    def __init__(self) -> None:
        self._sina = SinaKlineClient()

    async def fetch(self, code: str, period: str = "daily") -> List[Dict]:
        """获取K线数据。

        Args:
            code: 纯数字股票代码，如 "000858"。
            period: "daily" / "weekly" / "monthly"。

        Returns:
            标准格式列表: [{trade_date, open, high, low, close, volume, amount}, ...]
        """
        try:
            data = await self._sina.fetch(code, period)
            if data:
                logger.info("K线数据来源: sina (%d 条, period=%s)", len(data), period)
                return data
        except Exception as exc:
            logger.warning("新浪K线获取失败 code=%s period=%s: %s", code, period, exc)

        logger.warning("K线数据源均失败: code=%s period=%s", code, period)
        return []
