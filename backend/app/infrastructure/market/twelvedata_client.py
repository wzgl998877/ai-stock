"""TwelveData 分时数据客户端（增强源）。

免费层限制 800 次/天，API Key 未配置时静默返回空列表。
"""

import logging
from typing import List, Dict

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


def _exchange(code: str) -> str:
    """根据代码判断交易所。"""
    if code.startswith("6"):
        return "XSHG"  # 上海
    return "XSHE"  # 深圳


class TwelveDataMinuteClient:
    """TwelveData 5分钟K线客户端。"""

    def __init__(self) -> None:
        self._url = "https://api.twelvedata.com/time_series"

    async def fetch(self, code: str) -> List[Dict]:
        """获取5分钟K线数据。API Key 未配置时直接返回空列表。"""
        api_key = settings.twelvedata_api_key
        if not api_key:
            return []

        exchange = _exchange(code)
        params = {
            "symbol": code,
            "exchange": exchange,
            "interval": "5min",
            "outputsize": 30,
            "apikey": api_key,
        }

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(self._url, params=params)
            resp.raise_for_status()
            payload = resp.json()

        # TwelveData 返回 {"values": [...]} 或 {"status": "error", ...}
        values = payload.get("values", [])
        if not values:
            if payload.get("status") == "error":
                logger.warning("TwelveData 错误: %s", payload.get("message", ""))
            return []

        # TwelveData 返回倒序，需要翻转
        values = list(reversed(values))

        result: List[Dict] = []
        cum_volume = 0.0
        cum_amount = 0.0

        for item in values:
            close_price = float(item.get("close", 0))
            vol = float(item.get("volume", 0))
            datetime_str = item.get("datetime", "")

            if close_price <= 0:
                continue

            # 提取时间部分 (格式 "2025-01-01 09:30:00")
            time_part = ""
            if " " in datetime_str:
                time_part = datetime_str.split(" ")[1][:5]

            cum_volume += vol
            cum_amount += close_price * vol
            avg = cum_amount / cum_volume if cum_volume > 0 else close_price

            result.append({
                "time": time_part,
                "price": close_price,
                "volume": vol,
                "avg_price": round(avg, 2),
            })

        return result
