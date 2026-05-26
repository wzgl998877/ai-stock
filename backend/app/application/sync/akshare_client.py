"""AKShare 数据源客户端。

AKShare 是免费的 A 股数据接口，无需认证。
获取基础信息、实时行情、日K线、财务摘要等原始数据。
返回结果为 List[Dict]，后续由 data_cleaner 服务清洗后入库。

使用方式:
    client = AKShareClient()
    stocks = client.fetch_basic_info()
    quotes = client.fetch_quote(["000001", "600000"])
"""

import logging
import time
from typing import Optional, List, Dict, Any

import akshare as ak
import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 全局 patch：让 AKShare 底层请求使用 curl_cffi（绕过东方财富反爬）
# 只执行一次，模块加载时自动触发
# ---------------------------------------------------------------------------

def _patch_akshare_with_curl_cffi():
    """Monkey-patch requests.get 使 AKShare 的东方财富请求走 curl_cffi。"""
    try:
        from curl_cffi import requests as curl_requests
    except ImportError:
        logger.debug("curl_cffi 未安装，跳过 patch")
        return False

    import requests

    if hasattr(requests, '_akshare_curl_patched'):
        return True

    original_get = requests.get
    _last_request_time = {'time': 0}

    def patched_get(url, **kwargs):
        # 只对东方财富的请求添加延迟 + curl_cffi
        if 'eastmoney.com' in url:
            # 请求延迟，避免被反爬封禁
            now = time.time()
            elapsed = now - _last_request_time['time']
            if elapsed < 0.5:
                time.sleep(0.5 - elapsed)
            _last_request_time['time'] = time.time()

            # 使用 curl_cffi 模拟 Chrome 浏览器 TLS 指纹
            try:
                curl_kwargs = {
                    'timeout': kwargs.get('timeout', 30),
                    'impersonate': 'chrome120',
                }
                if 'params' in kwargs:
                    curl_kwargs['params'] = kwargs['params']
                if 'headers' in kwargs:
                    curl_kwargs['headers'] = kwargs['headers']
                if 'data' in kwargs:
                    curl_kwargs['data'] = kwargs['data']
                if 'json' in kwargs:
                    curl_kwargs['json'] = kwargs['json']

                response = curl_requests.get(url, **curl_kwargs)
                logger.debug("[curl_cffi] %s → %d", url[:80], response.status_code)
                return response
            except Exception as e:
                logger.warning("curl_cffi 请求失败，回退到 requests: %s", e)

        # 非东方财富请求 或 curl_cffi 失败 → 原始 requests
        return original_get(url, **kwargs)

    requests.get = patched_get
    requests._akshare_curl_patched = True
    logger.info("已启用 curl_cffi 绕过东方财富反爬（模拟 Chrome 120）")
    return True


# 模块加载时自动 patch
_patch_akshare_with_curl_cffi()


class AKShareClient:
    """AKShare 数据源客户端。

    所有方法均为同步阻塞调用，错误时返回空列表并记录日志。
    AKShare 不需要 API 认证。
    """

    # 交易所前缀映射
    _EXCHANGE_PREFIX_SH = {"6"}  # 6 开头 = 上海
    _EXCHANGE_PREFIX_SZ = {"0", "3"}  # 0/3 开头 = 深圳
    _EXCHANGE_PREFIX_BJ = {"4", "8"}  # 4/8 开头 = 北京

    def __init__(self) -> None:
        """初始化 AKShare 客户端（无需认证）。"""
        logger.info("AKShareClient 初始化完成")

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    @staticmethod
    def _infer_exchange(code: str) -> str:
        """根据股票代码前缀推断交易所。

        Args:
            code: 纯数字股票代码。

        Returns:
            "SH", "SZ", "BJ" 或空字符串。
        """
        if not code:
            return ""
        first_char = code[0]
        if first_char in AKShareClient._EXCHANGE_PREFIX_SH:
            return "SH"
        if first_char in AKShareClient._EXCHANGE_PREFIX_SZ:
            return "SZ"
        if first_char in AKShareClient._EXCHANGE_PREFIX_BJ:
            return "BJ"
        return ""

    @staticmethod
    def _df_to_records(df) -> List[Dict[str, Any]]:
        """安全地将 DataFrame 转换为记录列表。

        Args:
            df: pandas DataFrame。

        Returns:
            记录列表，转换失败时返回空列表。
        """
        if df is None or not isinstance(df, pd.DataFrame):
            return []
        return df.to_dict("records")

    def _safe_call(self, method_name: str, func, *args, **kwargs) -> List[Dict[str, Any]]:
        """统一的安全调用包装器，带指数退避重试。

        Args:
            method_name: 方法名称（用于日志）
            func: 要调用的函数
            *args, **kwargs: 传递给 func 的参数

        Returns:
            函数返回的 list[dict]，异常时返回空列表。
        """
        import time

        max_retries = 3
        for attempt in range(max_retries):
            try:
                df = func(*args, **kwargs)
                records = self._df_to_records(df)
                logger.info("AKShare %s 成功，获取 %d 条记录", method_name, len(records))
                return records
            except Exception as e:
                if attempt < max_retries - 1:
                    wait = 2 ** attempt  # 1s, 2s, 4s
                    logger.warning("AKShare %s 调用异常(第%d次重试): %s", method_name, attempt + 1, str(e))
                    time.sleep(wait)
                else:
                    logger.error("AKShare %s 调用异常(重试耗尽): %s", method_name, str(e), exc_info=True)
                    return []

    # ------------------------------------------------------------------
    # 公开方法
    # ------------------------------------------------------------------

    def fetch_basic_info(self) -> List[Dict[str, Any]]:
        """获取所有 A 股股票的基础信息。

        使用 ak.stock_info_a_code_name() 获取代码和名称。

        Returns:
            List of dicts with keys: code, name, exchange
        """
        logger.info("AKShare 获取股票基础信息...")

        def _call():
            return ak.stock_info_a_code_name()

        records = self._safe_call("fetch_basic_info", _call)

        result = []
        for row in records:
            code = row.get("code", "")
            result.append({
                "code": code,
                "name": row.get("name", ""),
                "exchange": self._infer_exchange(code),
                "industry": None,
                "list_date": None,
            })

        logger.info("AKShare fetch_basic_info 完成，共 %d 条", len(result))
        return result

    def fetch_quote(self, codes: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """获取 A 股实时行情数据。

        使用 ak.stock_zh_a_spot_em() 获取全市场实时行情。
        如果传入 codes，则过滤结果。

        Args:
            codes: 可选，股票代码列表。为 None 时返回全市场。

        Returns:
            List of dicts with keys: code, price, change_pct, change_amount,
            volume, amount, open, high, low, pre_close
        """
        logger.info("AKShare 获取实时行情，过滤股票数: %s", len(codes) if codes else "全部")

        def _call():
            return ak.stock_zh_a_spot_em()

        records = self._safe_call("fetch_quote", _call)

        # 如果指定了 codes，进行过滤
        if codes:
            code_set = set(codes)
            records = [r for r in records if r.get("代码", "") in code_set]

        result = []
        for row in records:
            result.append({
                "code": row.get("代码", ""),
                "price": row.get("最新价"),
                "change_pct": row.get("涨跌幅"),
                "change_amount": row.get("涨跌额"),
                "volume": row.get("成交量"),
                "amount": row.get("成交额"),
                "open": row.get("今开"),
                "high": row.get("最高"),
                "low": row.get("最低"),
                "pre_close": row.get("昨收"),
            })

        logger.info("AKShare fetch_quote 完成，共 %d 条", len(result))
        return result

    def fetch_daily_quote(
        self,
        code: str,
        start_date: str,
        end_date: str,
        period: str = "daily",
    ) -> List[Dict[str, Any]]:
        """获取指定股票的历史日K线行情数据。

        使用 ak.stock_zh_a_hist() 获取前复权历史行情。

        Args:
            code: 股票代码（纯数字，如 "000001"）。
            start_date: 开始日期，格式 "YYYYMMDD"。
            end_date: 结束日期，格式 "YYYYMMDD"。
            period: 周期，"daily"（日线）、"weekly"（周线）、"monthly"（月线）。

        Returns:
            List of dicts with keys: code, trade_date, open, high, low, close,
            volume, amount, pct_chg, pre_close, period
        """
        # AKShare 的 period 参数映射
        ak_period_map = {
            "daily": "daily",
            "weekly": "weekly",
            "monthly": "monthly",
        }
        ak_period = ak_period_map.get(period, "daily")

        # AKShare 要求 YYYYMMDD 格式，兼容前端传入的 YYYY-MM-DD
        sd = start_date.replace("-", "")
        ed = end_date.replace("-", "")

        logger.info(
            "AKShare 获取日K线: code=%s, start=%s, end=%s, period=%s",
            code, sd, ed, ak_period,
        )

        def _call():
            return ak.stock_zh_a_hist(
                symbol=code,
                period=ak_period,
                start_date=sd,
                end_date=ed,
                adjust="qfq",  # 前复权
            )

        records = self._safe_call("fetch_daily_quote", _call)

        result = []
        for row in records:
            result.append({
                "code": code,
                "trade_date": row.get("日期"),
                "open": row.get("开盘"),
                "high": row.get("最高"),
                "low": row.get("最低"),
                "close": row.get("收盘"),
                "volume": row.get("成交量"),
                "amount": row.get("成交额"),
                "pct_chg": row.get("涨跌幅"),
                "pre_close": row.get("前收盘"),
                "period": period,
            })

        logger.info("AKShare fetch_daily_quote 完成，共 %d 条", len(result))
        return result

    def fetch_financial(self, code: str) -> List[Dict[str, Any]]:
        """获取指定股票的财务摘要数据。

        使用 ak.stock_financial_abstract_ths() 获取财务摘要，
        返回最近 4 个季度的数据。

        Args:
            code: 股票代码（纯数字，如 "000001"）。

        Returns:
            List of dicts with keys: code, report_date, roe, net_profit,
            revenue, eps, gross_margin, debt_ratio
        """
        logger.info("AKShare 获取财务摘要: code=%s", code)

        def _call():
            return ak.stock_financial_abstract_ths(symbol=code)

        records = self._safe_call("fetch_financial", _call)

        # 只取最近 4 个季度
        if len(records) > 4:
            records = records[-4:]

        result = []
        for row in records:
            # 兼容不同 AKShare 版本的列名（stock_financial_abstract_ths 实际列名）
            report_date = (
                row.get("报告期")
                or row.get("报告日期")
                or row.get("report_date")
                or row.get("date")
            )
            roe = (
                row.get("净资产收益率")
                or row.get("净资产收益率(%)")
                or row.get("roe")
                or row.get("ROE")
            )
            net_profit = (
                row.get("净利润")
                or row.get("净利润(元)")
                or row.get("net_profit")
            )
            revenue = (
                row.get("营业总收入")
                or row.get("营业收入")
                or row.get("营业收入(元)")
                or row.get("revenue")
            )
            eps = (
                row.get("基本每股收益")
                or row.get("每股收益(元)")
                or row.get("每股收益")
                or row.get("eps")
            )
            gross_margin = (
                row.get("销售毛利率")
                or row.get("毛利率(%)")
                or row.get("毛利率")
                or row.get("gross_margin")
            )
            debt_ratio = (
                row.get("资产负债率")
                or row.get("资产负债率(%)")
                or row.get("debt_ratio")
            )

            result.append({
                "code": code,
                "report_date": report_date,
                "roe": roe,
                "net_profit": net_profit,
                "revenue": revenue,
                "eps": eps,
                "gross_margin": gross_margin,
                "debt_ratio": debt_ratio,
            })

        logger.info("AKShare fetch_financial 完成，共 %d 条", len(result))
        return result
