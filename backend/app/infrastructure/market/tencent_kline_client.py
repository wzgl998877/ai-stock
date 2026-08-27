"""腾讯财经K线数据客户端（日K/周K/月K/30分钟K）。

接口:
- 日/周/月K: web.ifzq.gtimg.cn/appstock/app/fqkline/get（前复权）
- 30分钟K:   ifzq.gtimg.cn/appstock/app/kline/mkline（分钟线，param={code},m30,,{count}）

新浪 K 线被限流封禁（456）时的降级源（2026-08-25 引入）。
"""

import json
import logging
import re
from typing import Dict, List

import httpx

from app.infrastructure.market.tencent_client import _prefix_code

logger = logging.getLogger(__name__)

# 腾讯K线周期 -> 接口参数 & 返回字段 key
_PERIOD_MAP = {
    "daily":   ("day",    "qfqday"),
    "weekly":  ("week",   "qfqweek"),
    "monthly": ("month",  "qfqmonth"),
}

# 默认拉取条数
_COUNT_MAP = {
    "daily":   500,
    "weekly":  200,
    "monthly": 120,
    "m30":     640,   # ≈ 80 个交易日（8 根/日），覆盖回补与增量缺口
}


def _parse_m30_time(ts: str) -> str:
    """腾讯分钟线时间戳 ``202608251500`` → ``2026-08-25 15:00:00``。

    与新浪 m30 口径一致：时间戳为**区间结束时刻**（1330 → 13:30 那根收盘）。
    """
    return f"{ts[0:4]}-{ts[4:6]}-{ts[6:8]} {ts[8:10]}:{ts[10:12]}:00"


class TencentKlineClient:
    """腾讯财经K线数据客户端。"""

    def __init__(self) -> None:
        # param 六段格式：code,type,start,end,count,fq（start/end 留空拉最近
        # count 根）。此前少一段（…,{type},,{count},qfq）被接口判 "param error"，
        # 且错误响应的 data 是列表 []，曾导致上层对列表调 .get 抛
        # 'list' object has no attribute 'get'（2026-08-27 日线降级全量失败）
        self._base_url = (
            "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
            "?_var=kline_{type}qfq&param={code},{type},,,{count},qfq"
        )

    async def fetch(self, code: str, period: str = "daily", count: int | None = None) -> List[Dict]:
        """获取K线数据。

        Args:
            code: 纯数字股票代码，如 "000858"。
            period: "daily" / "weekly" / "monthly" / "m30"。
            count: 拉取条数；None 用 ``_COUNT_MAP`` 默认值。增量同步传小值。

        Returns:
            标准格式列表: [{trade_date, open, high, low, close, volume, amount}, ...]

            - 日/周/月K：``trade_date`` 为日期串 ``"2026-05-06"``；
            - 30分钟K：``trade_date`` 为区间结束时刻 ``"2026-05-06 10:00:00"``
              （与新浪 m30 口径一致，每交易日 8 根）。
        """
        if period == "m30":
            return await self._fetch_m30(code, count)
        type_param, data_key = _PERIOD_MAP.get(period, ("day", "qfqday"))
        datalen = max(1, count if count is not None else _COUNT_MAP.get(period, 500))
        prefixed = _prefix_code(code)

        url = self._base_url.format(type=type_param, code=prefixed, count=datalen)

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                text = resp.text
        except Exception as exc:
            logger.warning("腾讯K线请求失败 code=%s period=%s: %s", code, period, exc)
            return []

        # 去掉 JS 变量前缀: "kline_weekqfq={...}" 或 "kline_monthqfq={...}"
        text = re.sub(r"^(var\s+)?\w+\s*=\s*", "", text.strip())
        if text.endswith(";"):
            text = text[:-1]
        if not text:
            return []

        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            logger.warning("腾讯K线JSON解析失败 code=%s", code)
            return []

        # 数据路径: data -> {prefixed_code} -> {data_key}。
        # 错误响应（如 "param error"）的 data 是列表 []，非字典——防御式取值，
        # 避免对列表调 .get 抛 'list' object has no attribute 'get'
        stock_data = payload.get("data")
        if not isinstance(stock_data, dict):
            logger.warning(
                "腾讯K线响应异常（data 非字典，多为 param error）code=%s period=%s msg=%s",
                code, period, payload.get("msg"),
            )
            return []
        code_data = stock_data.get(prefixed, {})
        raw_list = code_data.get(data_key, [])
        if not raw_list:
            # 尝试 qfqday 作为 fallback（日K返回 qfqday）
            raw_list = code_data.get("qfqday", [])
        if not raw_list:
            return []

        result: List[Dict] = []
        for row in raw_list:
            if not row or len(row) < 6:
                continue
            # 腾讯K线字段顺序: [date, open, close, low, high, volume]
            # 注意: close 在 high 前面
            try:
                item = {
                    "trade_date": row[0],
                    "open": float(row[1]) if row[1] else None,
                    "close": float(row[2]) if row[2] else None,
                    "low": float(row[3]) if row[3] else None,
                    "high": float(row[4]) if row[4] else None,
                    "volume": float(row[5]) if row[5] else None,
                    "amount": None,  # 腾讯接口不返回成交额
                }
                result.append(item)
            except (ValueError, IndexError) as e:
                logger.debug("腾讯K线行解析跳过: %s", e)
                continue

        logger.info("腾讯K线获取成功 code=%s period=%s count=%d", code, period, len(result))
        return result

    async def _fetch_m30(self, code: str, count: int | None = None) -> List[Dict]:
        """30 分钟 K 线（mkline 接口，新浪封禁时的降级源）。

        返回行字段顺序: [time, open, close, high, low, volume]——注意 close 在
        high **前**（与日K相同）；时间戳 ``202608251500`` 为区间结束时刻。
        """
        datalen = max(1, count if count is not None else _COUNT_MAP["m30"])
        prefixed = _prefix_code(code)
        url = f"https://ifzq.gtimg.cn/appstock/app/kline/mkline?param={prefixed},m30,,{datalen}"

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                text = resp.text
        except Exception as exc:
            logger.warning("腾讯m30请求失败 code=%s: %s", code, exc)
            return []

        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            logger.warning("腾讯m30 JSON解析失败 code=%s", code)
            return []

        stock_data = payload.get("data")
        if not isinstance(stock_data, dict):
            logger.warning("腾讯m30响应异常（data 非字典）code=%s", code)
            return []
        raw_list = stock_data.get(prefixed, {}).get("m30", [])
        result: List[Dict] = []
        for row in raw_list:
            if not row or len(row) < 6:
                continue
            try:
                item = {
                    "trade_date": _parse_m30_time(str(row[0])),
                    "open": float(row[1]) if row[1] else None,
                    "close": float(row[2]) if row[2] else None,
                    "high": float(row[3]) if row[3] else None,
                    "low": float(row[4]) if row[4] else None,
                    "volume": float(row[5]) if row[5] else None,
                    "amount": None,
                }
                result.append(item)
            except (ValueError, IndexError) as e:
                logger.debug("腾讯m30行解析跳过: %s", e)
                continue

        logger.info("腾讯m30获取成功 code=%s count=%d", code, len(result))
        return result
