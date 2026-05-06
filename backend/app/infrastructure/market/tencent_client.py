"""腾讯财经分时数据客户端。

分时接口: web.ifzq.gtimg.cn/appstock/app/minute/query
"""

import json
import logging
import re
from typing import Dict, List

import httpx

logger = logging.getLogger(__name__)


def _prefix_code(code: str) -> str:
    """将纯数字代码转为带市场前缀的代码，如 600519 -> sh600519。"""
    if code.startswith(("sh", "sz")):
        return code
    if code.startswith("6"):
        return f"sh{code}"
    return f"sz{code}"


class TencentMinuteClient:
    """腾讯财经分时数据客户端。"""

    def __init__(self) -> None:
        self._minute_url = (
            "https://web.ifzq.gtimg.cn/appstock/app/minute/query"
            "?_var=min_data&code={code}"
        )

    async def fetch(self, code: str) -> List[Dict]:
        """获取分时数据。"""
        prefixed = _prefix_code(code)
        url = self._minute_url.format(code=prefixed)

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            text = resp.text

        # 去掉前缀: "min_data=..." 或 "var min_data=..."
        text = re.sub(r"^(var\s+)?\w+\s*=\s*", "", text.strip())
        if not text or text == ";":
            return []

        payload = json.loads(text)

        # 检查返回码
        if payload.get("code") != 0:
            logger.warning("腾讯分时接口返回错误: %s", payload.get("msg"))
            return []

        # 数据在 data -> {code} -> data -> data 字段下
        stock_data = payload.get("data", {})
        code_data = stock_data.get(prefixed, {})
        minute_raw = code_data.get("data", {}).get("data", [])
        if not minute_raw:
            return []

        # 解析每分钟数据，格式为 "0930 价格 累计成交量 累计成交额"
        # 注意：第2、3个字段是累计值，需做差分得到增量
        result: List[Dict] = []
        prev_cum_vol = 0.0

        for entry in minute_raw:
            parts = entry.split()
            if len(parts) < 4:
                continue
            t = parts[0]  # 格式 "0930"
            price = float(parts[1])
            cum_vol = float(parts[2])
            cum_amt = float(parts[3])

            # 增量成交量
            vol = cum_vol - prev_cum_vol
            prev_cum_vol = cum_vol

            # 均价 = 累计成交额 / (累计成交量 × 100)
            # 腾讯成交量单位为"手"(100股)，成交额单位为"元"
            avg = cum_amt / (cum_vol * 100) if cum_vol > 0 else price

            # 格式化时间为 "09:30"
            time_fmt = f"{t[:2]}:{t[2:]}" if len(t) == 4 else t

            result.append({
                "time": time_fmt,
                "price": price,
                "volume": vol,
                "avg_price": round(avg, 2),
            })

        return result
