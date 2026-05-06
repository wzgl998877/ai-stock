"""腾讯财经K线数据客户端（日K/周K/月K）。

接口: web.ifzq.gtimg.cn/appstock/app/fqkline/get
支持前复权日K、周K、月K数据。
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
}


class TencentKlineClient:
    """腾讯财经K线数据客户端。"""

    def __init__(self) -> None:
        self._base_url = (
            "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
            "?_var=kline_{type}qfq&param={code},{type},,{count},qfq"
        )

    async def fetch(self, code: str, period: str = "daily") -> List[Dict]:
        """获取K线数据。

        Args:
            code: 纯数字股票代码，如 "000858"。
            period: "daily" / "weekly" / "monthly"。

        Returns:
            标准格式列表: [{trade_date, open, high, low, close, volume, amount}, ...]
        """
        type_param, data_key = _PERIOD_MAP.get(period, ("day", "qfqday"))
        count = _COUNT_MAP.get(period, 500)
        prefixed = _prefix_code(code)

        url = self._base_url.format(type=type_param, code=prefixed, count=count)

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

        # 数据路径: data -> {prefixed_code} -> {data_key}
        stock_data = payload.get("data", {})
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
