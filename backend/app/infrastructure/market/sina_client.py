"""新浪财经5分钟K线数据客户端。"""

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


class SinaMinuteClient:
    """新浪财经5分钟K线客户端。"""

    def __init__(self) -> None:
        self._url = (
            "https://quotes.sina.cn/cn/api/jsonp_v2.php/var%20data"
            "/CN_MarketDataService.getKLineData?symbol={code}&scale=5&datalen=48"
        )

    async def fetch(self, code: str) -> List[Dict]:
        """获取5分钟K线数据。"""
        prefixed = _prefix_code(code)
        url = self._url.format(code=prefixed)

        headers = {"Referer": "https://finance.sina.com"}

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            text = resp.text

        # 去除 JSONP 包裹和可能的 script 前缀
        # 实际返回: /*<script>...</script>*/\nvar data([...]);
        text = re.sub(r"^/\*<script>.*?</script>\*/", "", text.strip(), flags=re.DOTALL)
        # 去除 "var data(" 前缀和 ");" 后缀
        match = re.search(r"\((\[.*\])\)", text, re.DOTALL)
        if not match:
            return []

        items = json.loads(match.group(1))
        if not isinstance(items, list) or not items:
            return []

        result: List[Dict] = []
        cum_volume = 0.0
        cum_amount = 0.0

        for item in items:
            # 新浪字段: day, open, high, low, close, volume, amount
            day_str = item.get("day", "")
            close_price = float(item.get("close", 0))
            vol = float(item.get("volume", 0))
            amt = float(item.get("amount", 0))

            if close_price <= 0:
                continue

            # 提取时间部分 "2026-05-06 09:35:00" -> "09:35"
            if " " in day_str:
                time_part = day_str.split(" ")[1][:5]
            else:
                time_part = day_str

            cum_volume += vol
            cum_amount += amt
            avg = cum_amount / cum_volume if cum_volume > 0 else close_price

            result.append({
                "time": time_part,
                "price": close_price,
                "volume": vol,
                "avg_price": round(avg, 2),
            })

        return result
