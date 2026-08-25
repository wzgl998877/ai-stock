"""30 分钟 K 线历史回补 / 增量同步（模块三，独立表 ``t_stock_kline_30m``）。

数据源主：新浪 ``scale=30``（单次上限 ~1500 根 ≈ 9 个月，无分页）；
降级：腾讯 ``mkline``（新浪被限流封禁 456 / 返回空时切换，2026-08-25 引入）。
- 首次回补：库中无数据 → 拉取最近 ~1500 根作为初始历史；
- 日常增量：库中有数据 → 只拉最近 ``INCREMENT_COUNT`` 根（覆盖近 2 个交易日），
  按 ``trade_time`` 去重合并——**大幅缩小请求体积**，避免新浪按 IP 限流封禁
  （2026-08-25 生产事故：36 股 × 8 时点/日 × datalen=1500 全量拉，触发 456 封禁，
  数据断档两日、监控大面积 no_new_data 跳过）。

存储走独立表（见 memory chanlun-30m-storage-decision），不复用 ``t_stock_daily_quote``。
对标 ``sync_executor`` 的拉取→清洗→upsert→清缓存 范式，但聚焦 30m。
"""

import logging
from datetime import datetime
from decimal import Decimal

from app.domain.models.stock_data import StockKline30m
from app.infrastructure.market.sina_kline_client import SinaKlineClient
from app.infrastructure.market.tencent_kline_client import TencentKlineClient

logger = logging.getLogger(__name__)

SOURCE = "sina"

# 增量拉取条数：每交易日 8 根，20 根 ≈ 2.5 个交易日（覆盖周末/节假日缺口 +
# 当日盘中已走完的根），即使前几轮同步失败也能一轮补齐。
INCREMENT_COUNT = 20


def _to_decimal(v) -> Decimal | None:
    return Decimal(str(v)) if v is not None else None


async def _fetch_raw(code: str, count: int | None) -> tuple[list[dict], str]:
    """拉取原始 K 线：新浪 → 腾讯降级。返回 (raw_list, source)。

    新浪"空返回"既可能是真无数据也可能是被限流（HTTP 200 空数组，比 456 更
    隐蔽），统一降级腾讯再试一次：腾讯有数据则以腾讯结果为准；两边都空才视为
    真无数据。
    """
    sina = await SinaKlineClient().fetch(code, period="m30", count=count)
    if sina:
        return sina, "sina"
    logger.info("[30m同步] 新浪无数据/被限流，降级腾讯 code=%s", code)
    tencent = await TencentKlineClient().fetch(code, period="m30", count=count)
    return tencent, "tencent"


async def sync_stock_30m(code: str, stock_data_repo) -> int:
    """拉取 ``code`` 的 30 分钟 K 线并落库（先删后插，按 trade_time 去重）。

    增量策略：库中已有该股数据时只拉 ``INCREMENT_COUNT`` 根（去重合并），
    无数据时全量回补 1500 根。新浪拉不到自动降级腾讯。

    Returns:
        落库条数（0 表示无数据）。
    """
    latest = await stock_data_repo.get_latest_kline_30m_time(code)
    count = None if latest is None else INCREMENT_COUNT
    raw_list, source = await _fetch_raw(code, count)
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
        if latest is not None and trade_time <= latest:
            # 增量模式：已有最新行及更早的都跳过（含库内最新行重写，upsert 也幂等，
            # 但跳过可减少删除重插的写放大）
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
            data_source=source,
        ))

    if not quotes:
        return 0

    await stock_data_repo.upsert_kline_30m_batch(quotes)
    await _clear_kline_30m_cache(code)
    logger.info("[30m同步] code=%s 落库 %d 根（%s/%s）", code, len(quotes),
                "增量" if latest is not None else "回补", source)
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
