"""新浪财经同步客户端。

实现与 AKShareClient 相同的接口，用于 K 线数据同步降级。
新浪财经无需认证，支持 daily/weekly/monthly 三种周期。

限制:
- datalen 上限约 1950 条（约 8 年日 K 数据）
- 不返回 pct_chg / pre_close，需自行计算
- 不支持 basic_info / quote / financial，仅支持 daily_quote
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


def _prefix_code(code: str) -> str:
    """纯数字代码 -> 新浪格式，如 600519 -> sh600519。"""
    if code.startswith(("sh", "sz")):
        return code
    if code.startswith("6"):
        return f"sh{code}"
    return f"sz{code}"


class SinaSyncClient:
    """新浪财经同步客户端（同步 HTTP 调用）。"""

    # 新浪 K 线 scale 映射
    _SCALE_MAP = {
        "daily": 240,
        "weekly": 1200,
        "monthly": 7200,
    }

    def __init__(self) -> None:
        logger.info("SinaSyncClient 初始化完成")

    def fetch_basic_info(self) -> List[Dict[str, Any]]:
        """新浪不支持批量基础信息同步。"""
        logger.warning("[SinaSyncClient] fetch_basic_info 不支持")
        return []

    def fetch_quote(self, codes: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """新浪不支持实时行情批量同步。"""
        logger.warning("[SinaSyncClient] fetch_quote 不支持")
        return []

    def fetch_daily_quote(
        self,
        code: str,
        start_date: str,
        end_date: str,
        period: str = "daily",
    ) -> List[Dict[str, Any]]:
        """获取历史 K 线数据（同步调用新浪 API）。

        Args:
            code: 纯数字股票代码，如 "000001"。
            start_date: 起始日期 YYYY-MM-DD 或 YYYYMMDD。
            end_date: 结束日期。
            period: "daily" / "weekly" / "monthly"。

        Returns:
            与 AKShareClient 相同格式的列表。
        """
        scale = self._SCALE_MAP.get(period, 240)

        # 计算需要拉取的条数（交易日近似）
        from datetime import datetime, timedelta

        sd = datetime.strptime(start_date.replace("-", ""), "%Y%m%d")
        ed = datetime.strptime(end_date.replace("-", ""), "%Y%m%d")
        days = (ed - sd).days
        if period == "daily":
            datalen = min(days // 365 * 250 + 300, 1950)
        elif period == "weekly":
            datalen = min(days // 7 + 10, 1950)
        else:
            datalen = min(days // 30 + 10, 1950)
        # 下限 10 根（非交易日近似换算），兼顾：增量同步缺口小（几天）时请求体积小，
        # 且停牌/节假日多日无新行时仍能取到窗口内数据。此前下限 60 根对增量场景
        # 偏大（新浪按 IP 限流，datalen 越大越易被封，见 2026-08-25 456 封禁事故）。
        datalen = max(datalen, 10)

        prefixed = _prefix_code(code)
        url = (
            f"https://quotes.sina.cn/cn/api/jsonp_v2.php/var%20data"
            f"/CN_MarketDataService.getKLineData"
            f"?symbol={prefixed}&scale={scale}&datalen={datalen}"
        )
        headers = {"Referer": "https://finance.sina.com"}

        try:
            with httpx.Client(timeout=15) as client:
                resp = client.get(url, headers=headers)
                resp.raise_for_status()
                text = resp.text
        except Exception as exc:
            logger.error("[SinaSyncClient] 请求失败 code=%s: %s", code, exc)
            return []

        # JSONP 解析
        text = re.sub(r"^/\*<script>.*?</script>\*/", "", text.strip(), flags=re.DOTALL)
        match = re.search(r"\((\[.*\])\)", text, re.DOTALL)
        if not match:
            logger.warning("[SinaSyncClient] JSONP 解析失败 code=%s", code)
            return []

        try:
            items = json.loads(match.group(1))
        except json.JSONDecodeError:
            logger.warning("[SinaSyncClient] JSON 解析失败 code=%s", code)
            return []

        if not isinstance(items, list) or not items:
            return []

        # 转换为统一格式，并在过滤后计算 pct_chg / pre_close
        raw_records = []
        for item in items:
            day_str = item.get("day", "")
            trade_date = day_str.split(" ")[0] if " " in day_str else day_str
            raw_records.append({
                "trade_date": trade_date,
                "open": item.get("open"),
                "high": item.get("high"),
                "low": item.get("low"),
                "close": item.get("close"),
                "volume": item.get("volume"),
                "amount": item.get("amount"),
            })

        # 按日期过滤
        sd_str = start_date.replace("-", "")
        ed_str = end_date.replace("-", "")
        filtered = [
            r for r in raw_records
            if sd_str <= r["trade_date"].replace("-", "") <= ed_str
        ]

        # 计算 pre_close 和 pct_chg
        result = []
        for i, r in enumerate(filtered):
            pre_close = None
            pct_chg = None
            if i > 0:
                prev_close = filtered[i - 1]["close"]
                if prev_close and r["close"]:
                    try:
                        prev_f = float(prev_close)
                        cur_f = float(r["close"])
                        pre_close = prev_f
                        pct_chg = round((cur_f - prev_f) / prev_f * 100, 2) if prev_f else None
                    except (ValueError, ZeroDivisionError):
                        pass

            result.append({
                "code": code,
                "trade_date": r["trade_date"],
                "open": r["open"],
                "high": r["high"],
                "low": r["low"],
                "close": r["close"],
                "volume": r["volume"],
                "amount": r.get("amount") or None,
                "pct_chg": pct_chg,
                "pre_close": pre_close,
                "period": period,
            })

        logger.info("[SinaSyncClient] fetch_daily_quote 完成 code=%s period=%s count=%d", code, period, len(result))
        return result

    def fetch_financial(self, code: str) -> List[Dict[str, Any]]:
        """新浪不支持财务数据同步。"""
        logger.warning("[SinaSyncClient] fetch_financial 不支持")
        return []
