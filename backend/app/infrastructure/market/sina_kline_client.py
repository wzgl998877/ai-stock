"""新浪财经K线数据客户端（日K/周K/月K）。

接口: quotes.sina.cn/cn/api/jsonp_v2.php/.../CN_MarketDataService.getKLineData
"""

import json
import logging
import re
from typing import Dict, List

import httpx

logger = logging.getLogger(__name__)


def _prefix_code(code: str) -> str:
    """将纯数字代码转为新浪格式，如 600519 -> sh600519。"""
    if code.startswith(("sh", "sz")):
        return code
    if code.startswith("6"):
        return f"sh{code}"
    return f"sz{code}"


# 新浪K线 scale 映射
_SCALE_MAP = {
    "daily":   240,
    "weekly":  1200,
    "monthly": 7200,
}

# 新浪K线默认拉取条数
_COUNT_MAP = {
    "daily":   500,
    "weekly":  200,
    "monthly": 120,
}


class SinaKlineClient:
    """新浪财经K线数据客户端。"""

    def __init__(self) -> None:
        self._base_url = (
            "https://quotes.sina.cn/cn/api/jsonp_v2.php/var%20data"
            "/CN_MarketDataService.getKLineData"
            "?symbol={code}&scale={scale}&datalen={count}"
        )

    async def fetch(self, code: str, period: str = "daily") -> List[Dict]:
        """获取K线数据。

        Args:
            code: 纯数字股票代码，如 "000858"。
            period: "daily" / "weekly" / "monthly"。

        Returns:
            标准格式列表: [{trade_date, open, high, low, close, volume, amount}, ...]
        """
        prefixed = _prefix_code(code)
        scale = _SCALE_MAP.get(period, 240)
        count = _COUNT_MAP.get(period, 500)

        url = self._base_url.format(code=prefixed, scale=scale, count=count)
        headers = {"Referer": "https://finance.sina.com"}

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url, headers=headers)
                resp.raise_for_status()
                text = resp.text
        except Exception as exc:
            logger.warning("新浪K线请求失败 code=%s period=%s: %s", code, period, exc)
            return []

        # JSONP 解析: 去除 /*<script>...</script>*/ 前缀和 "var data([...])" 包裹
        text = re.sub(r"^/\*<script>.*?</script>\*/", "", text.strip(), flags=re.DOTALL)
        match = re.search(r"\((\[.*\])\)", text, re.DOTALL)
        if not match:
            return []

        try:
            items = json.loads(match.group(1))
        except json.JSONDecodeError:
            logger.warning("新浪K线JSON解析失败 code=%s", code)
            return []

        if not isinstance(items, list) or not items:
            return []

        result: List[Dict] = []
        for item in items:
            try:
                day_str = item.get("day", "")
                # 提取日期部分 "2026-05-06 00:00:00" -> "2026-05-06"
                trade_date = day_str.split(" ")[0] if " " in day_str else day_str

                result.append({
                    "trade_date": trade_date,
                    "open": float(item.get("open", 0)) or None,
                    "high": float(item.get("high", 0)) or None,
                    "low": float(item.get("low", 0)) or None,
                    "close": float(item.get("close", 0)) or None,
                    "volume": float(item.get("volume", 0)) or None,
                    "amount": float(item.get("amount", 0)) or None,
                })
            except (ValueError, TypeError) as e:
                logger.debug("新浪K线行解析跳过: %s", e)
                continue

        logger.info("新浪K线获取成功 code=%s period=%s count=%d", code, period, len(result))
        return result
