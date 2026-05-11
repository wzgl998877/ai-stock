"""批量实时行情客户端（腾讯 + 新浪 fallback）。

使用腾讯 qt.gtimg.cn 批量接口，一次请求获取多只股票实时行情。
失败时 fallback 到新浪 hq.sinajs.cn 接口。
"""

import logging
import re
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional

import httpx

from app.infrastructure.cache.redis_cache import redis_cache

logger = logging.getLogger(__name__)


def _prefix(code: str) -> str:
    """纯数字代码 -> 带市场前缀。"""
    if code.startswith(("sh", "sz")):
        return code
    return f"sh{code}" if code.startswith("6") else f"sz{code}"


def _unprefix(code: str) -> str:
    """去除市场前缀。"""
    return code.replace("sh", "").replace("sz", "")


@dataclass
class LiveQuote:
    code: str
    name: str
    price: Optional[float] = None
    pre_close: Optional[float] = None
    open_price: Optional[float] = None
    high_price: Optional[float] = None
    low_price: Optional[float] = None
    change_pct: Optional[float] = None
    change_amount: Optional[float] = None
    volume: Optional[float] = None
    amount: Optional[float] = None
    quote_time: Optional[str] = None
    data_source: str = ""


def _calc_change(price: Optional[float], pre_close: Optional[float]):
    """根据现价和昨收计算涨跌额、涨跌幅。"""
    if price is not None and pre_close and pre_close > 0:
        amt = round(price - pre_close, 4)
        pct = round(amt / pre_close * 100, 2)
        return pct, amt
    return None, None


# ---- 腾讯财经批量行情 ----

async def _fetch_tencent(codes: List[str]) -> Dict[str, LiveQuote]:
    """通过 qt.gtimg.cn 批量获取行情。"""
    prefixed = [_prefix(c) for c in codes]
    url = "https://qt.gtimg.cn/q=" + ",".join(prefixed)

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        text = resp.text

    result: Dict[str, LiveQuote] = {}
    for line in text.split(";"):
        line = line.strip()
        if not line or "=" not in line:
            continue
        _, _, raw = line.partition("=")
        raw = raw.strip().strip('"')
        if not raw:
            continue
        fields = raw.split("~")
        if len(fields) < 35:
            continue
        try:
            code = fields[2]
            name = fields[1]
            price = float(fields[3]) if fields[3] else None
            pre_close = float(fields[4]) if fields[4] else None
            open_price = float(fields[5]) if fields[5] else None
            high_price = float(fields[33]) if fields[33] else None
            low_price = float(fields[34]) if fields[34] else None
            volume = float(fields[6]) if fields[6] else None
            amount = float(fields[37]) if len(fields) > 37 and fields[37] else None
            date_str = fields[30] if len(fields) > 30 and fields[30] else ""
            # fields[30] = "20260511161407" (YYYYMMDD + HHMMSS 合在一起)
            quote_time = None
            if date_str and len(date_str) >= 14:
                quote_time = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]} {date_str[8:10]}:{date_str[10:12]}:{date_str[12:14]}"

            # 腾讯自带的涨跌幅字段不一定可靠，自行计算
            change_pct, change_amount = _calc_change(price, pre_close)

            result[code] = LiveQuote(
                code=code, name=name, price=price, pre_close=pre_close,
                open_price=open_price, high_price=high_price, low_price=low_price,
                change_pct=change_pct, change_amount=change_amount,
                volume=volume, amount=amount,
                quote_time=quote_time, data_source="tencent",
            )
        except (ValueError, IndexError) as e:
            logger.warning("腾讯行情解析失败: %s", e)
    return result


# ---- 新浪财经批量行情 ----

async def _fetch_sina(codes: List[str]) -> Dict[str, LiveQuote]:
    """通过 hq.sinajs.cn 批量获取行情。"""
    prefixed = [_prefix(c) for c in codes]
    url = "https://hq.sinajs.cn/list=" + ",".join(prefixed)

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, headers={"Referer": "https://finance.sina.com"})
        resp.raise_for_status()
        text = resp.text

    result: Dict[str, LiveQuote] = {}
    for line in text.split("\n"):
        line = line.strip()
        if not line or "=" not in line:
            continue
        key, _, val = line.partition("=")
        val = val.strip().strip('";')
        if not val:
            continue
        fields = val.split(",")
        if len(fields) < 32:
            continue
        try:
            # 从 key 提取带前缀代码: var hq_str_sh600519 -> sh600519
            prefixed_code = re.sub(r"^var\s+hq_str_", "", key)
            code = _unprefix(prefixed_code)
            name = fields[0]
            open_price = float(fields[1]) if fields[1] else None
            pre_close = float(fields[2]) if fields[2] else None
            price = float(fields[3]) if fields[3] else None
            high_price = float(fields[4]) if fields[4] else None
            low_price = float(fields[5]) if fields[5] else None
            volume = float(fields[8]) if fields[8] else None
            amount = float(fields[9]) if fields[9] else None
            date_str = fields[30] if len(fields) > 30 else ""
            time_str = fields[31] if len(fields) > 31 else ""
            quote_time = f"{date_str} {time_str}".strip() or None

            change_pct, change_amount = _calc_change(price, pre_close)

            result[code] = LiveQuote(
                code=code, name=name, price=price, pre_close=pre_close,
                open_price=open_price, high_price=high_price, low_price=low_price,
                change_pct=change_pct, change_amount=change_amount,
                volume=volume, amount=amount,
                quote_time=quote_time, data_source="sina",
            )
        except (ValueError, IndexError) as e:
            logger.warning("新浪行情解析失败: %s", e)
    return result


# ---- 聚合入口 ----

CACHE_TTL = 30  # 秒


async def get_batch_quotes(codes: List[str]) -> Dict[str, LiveQuote]:
    """批量获取实时行情，带 Redis 缓存和多源 fallback。

    返回 {code: LiveQuote}，未获取到的不出现在结果中。
    """
    if not codes:
        return {}

    # 1. 查缓存
    result: Dict[str, LiveQuote] = {}
    missed: List[str] = []
    for code in codes:
        cached = redis_cache.get(f"stock:live_quote:{code}")
        if cached:
            result[code] = LiveQuote(**cached)
        else:
            missed.append(code)

    if not missed:
        return result

    # 2. 腾讯 → 新浪 fallback
    for name, fetcher in [("tencent", _fetch_tencent), ("sina", _fetch_sina)]:
        try:
            fetched = await fetcher(missed)
            if fetched:
                logger.info("实时行情来源: %s (%d/%d)", name, len(fetched), len(missed))
                for code, q in fetched.items():
                    redis_cache.set(f"stock:live_quote:{code}", asdict(q), ttl=CACHE_TTL)
                result.update(fetched)
                break
        except Exception as e:
            logger.warning("实时行情源 %s 失败: %s", name, e)

    return result
