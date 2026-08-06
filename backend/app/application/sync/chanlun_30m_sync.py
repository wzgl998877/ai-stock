"""30 分钟 K 线历史回补 / 增量同步（模块三，独立表 ``t_stock_kline_30m``）。

数据源：新浪 ``scale=30``（单次上限 ~1500 根 ≈ 9 个月，无分页）。
- 首次回补：拉取最近 ~1500 根作为初始历史；
- 日常增量：监控调度每日调用，追加当日 8 根（与既有数据按 ``trade_time`` 去重）。

存储走独立表（见 memory chanlun-30m-storage-decision），不复用 ``t_stock_daily_quote``。
对标 ``sync_executor`` 的拉取→清洗→upsert→清缓存 范式，但聚焦 30m。
"""

import logging
from datetime import datetime
from decimal import Decimal

from app.domain.models.stock_data import StockKline30m
from app.infrastructure.market.sina_kline_client import SinaKlineClient

logger = logging.getLogger(__name__)

SOURCE = "sina"


def _to_decimal(v) -> Decimal | None:
    return Decimal(str(v)) if v is not None else None


async def sync_stock_30m(code: str, stock_data_repo) -> int:
    """拉取 ``code`` 的 30 分钟 K 线并落库（先删后插，按 trade_time 去重）。

    Returns:
        落库条数（0 表示无数据）。
    """
    client = SinaKlineClient()
    raw_list = await client.fetch(code, period="m30")
    if not raw_list:
        logger.info("[30m同步] 无数据 code=%s", code)
        return 0

    quotes: list[StockKline30m] = []
    for raw in raw_list:
        ts = raw.get("trade_date")
        if not ts:
            continue
        try:
            trade_time = datetime.fromisoformat(ts)
        except ValueError:
            continue
        quotes.append(StockKline30m(
            code=code,
            trade_time=trade_time,
            open_price=_to_decimal(raw.get("open")),
            high_price=_to_decimal(raw.get("high")),
            low_price=_to_decimal(raw.get("low")),
            close_price=_to_decimal(raw.get("close")),
            volume=_to_decimal(raw.get("volume")),
            amount=_to_decimal(raw.get("amount")),
            data_source=SOURCE,
        ))

    if not quotes:
        return 0

    await stock_data_repo.upsert_kline_30m_batch(quotes)
    await _clear_kline_30m_cache(code)
    logger.info("[30m同步] code=%s 落库 %d 根", code, len(quotes))
    return len(quotes)


async def _clear_kline_30m_cache(code: str) -> None:
    """清除 30m K 线缓存（``stock:kline30m:{code}:*``）。"""
    try:
        from app.infrastructure.cache.redis_cache import redis_cache as _cache
        if not _cache._available:
            return
        client = await _cache._ensure_client()
        if client is None:
            return
        pattern = f"stock:kline30m:{code}:*"
        cursor = 0
        while True:
            cursor, keys = await client.scan(cursor, match=pattern, count=100)
            if keys:
                await client.delete(*keys)
            if cursor == 0:
                break
    except Exception as e:
        logger.warning("清除30m缓存失败 code=%s: %s", code, e)
