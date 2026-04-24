"""Tushare 数据源客户端。

从 Tushare Pro API 获取 A 股基础信息、实时行情、日K线、财务指标等原始数据。
返回结果为 List[Dict]，后续由 data_cleaner 服务清洗后入库。

使用方式:
    client = TushareClient(token="your_token")
    stocks = client.fetch_basic_info()
    quotes = client.fetch_quote(["000001.SZ", "600000.SH"])
"""

import logging
from typing import Optional, List, Dict, Any

import tushare as ts

from app.domain.models.stock_data import DataSourceConfig, SourceType

logger = logging.getLogger(__name__)


class TushareClient:
    """Tushare Pro API 同步客户端。

    所有方法均为同步阻塞调用，错误时返回空列表并记录日志。
    """

    # Tushare API 频率限制相关关键字（用于识别限流错误）
    _RATE_LIMIT_KEYWORDS = [
        "每分钟",
        "每分钟最多",
        "访问过于频繁",
        "rate limit",
        "frequency",
        "积分",
        "请提高积分",
    ]

    def __init__(self, token: Optional[str] = None) -> None:
        """初始化 Tushare 客户端。

        Args:
            token: Tushare Pro API Token。如果为 None，则从 settings 或
                   DataSourceConfig 中获取。
        """
        self._token = token or self._resolve_token()
        if not self._token:
            logger.warning("Tushare token 未配置，部分功能可能无法使用")
        else:
            ts.set_token(self._token)
        self._pro = ts.pro_api()
        logger.info("TushareClient 初始化完成")

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_token() -> Optional[str]:
        """按优先级解析 token: DataSourceConfig > settings > None。"""
        # 1. 优先从 settings 中读取（本地 .env 配置）
        #    settings 中未直接定义 tushare_token，但预留了 datasource_encryption_key
        #    此处返回 None，由调用方通过 DataSourceConfig 传入
        return None

    @staticmethod
    def _to_ts_code(code: str) -> str:
        """将纯数字股票代码转换为 Tushare ts_code 格式。

        Args:
            code: 股票代码，支持 "600132"、"600132.SH"、"000001.SZ" 等。

        Returns:
            Tushare 格式，如 "600132.SH"。
        """
        # 已经是 ts_code 格式
        if "." in code:
            return code

        # 纯数字：根据首位判断交易所
        if not code:
            return code
        first = code[0]
        if first in ("6",):
            return f"{code}.SH"
        elif first in ("0", "3"):
            return f"{code}.SZ"
        elif first in ("4", "8"):
            return f"{code}.BJ"
        return code

    @staticmethod
    def from_config(config: DataSourceConfig) -> "TushareClient":
        """从 DataSourceConfig 创建客户端。

        Args:
            config: 数据源配置，source_type 应为 SourceType.TUSHARE。
        """
        return TushareClient(token=config.api_key)

    def _is_rate_limit_error(self, error_message: str) -> bool:
        """判断错误消息是否为 Tushare 频率限制错误。"""
        msg = error_message.lower()
        return any(kw in msg for kw in self._RATE_LIMIT_KEYWORDS)

    def _safe_call(self, method_name: str, func, *args, **kwargs) -> List[Dict[str, Any]]:
        """统一的安全调用包装器。

        Args:
            method_name: 方法名称（用于日志）
            func: 要调用的函数
            *args, **kwargs: 传递给 func 的参数

        Returns:
            函数返回的 list[dict]，异常时返回空列表。
        """
        try:
            result = func(*args, **kwargs)
            if result is None:
                logger.warning("Tushare %s 返回 None", method_name)
                return []
            if not hasattr(result, "to_dict"):
                # 非 DataFrame 结果，尝试直接返回
                if isinstance(result, list):
                    return result
                logger.warning("Tushare %s 返回非 DataFrame 结果: %s", method_name, type(result))
                return []
            records = result.to_dict("records")
            logger.info("Tushare %s 成功，获取 %d 条记录", method_name, len(records))
            return records
        except Exception as e:
            error_msg = str(e)
            if self._is_rate_limit_error(error_msg):
                logger.warning("Tushare %s 触发频率限制: %s", method_name, error_msg)
            else:
                logger.error("Tushare %s 调用异常: %s", method_name, error_msg, exc_info=True)
            return []

    # ------------------------------------------------------------------
    # 公开方法
    # ------------------------------------------------------------------

    def fetch_basic_info(self) -> List[Dict[str, Any]]:
        """获取所有当前 Listed 股票的基础信息。

        Returns:
            List of dicts with keys: code, name, industry, list_date, exchange
        """
        logger.info("Tushare 获取股票基础信息...")

        def _call():
            return self._pro.stock_basic(exchange="", list_status="L")

        records = self._safe_call("fetch_basic_info", _call)

        result = []
        for row in records:
            ts_code = row.get("ts_code", "")
            # 移除交易所后缀: 000001.SZ -> 000001
            code = ts_code.split(".")[0] if "." in ts_code else ts_code

            # 从 ts_code 推断交易所
            suffix = ts_code.split(".")[-1] if "." in ts_code else ""
            exchange_map = {"SH": "SH", "SZ": "SZ", "BJ": "BJ"}
            exchange = exchange_map.get(suffix, "")

            result.append({
                "code": code,
                "name": row.get("name", ""),
                "industry": row.get("industry"),
                "list_date": row.get("list_date"),
                "exchange": exchange,
            })

        logger.info("Tushare fetch_basic_info 完成，共 %d 条", len(result))
        return result

    def fetch_quote(self, codes: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """获取实时行情数据。

        如果传入 codes，则获取指定股票的实时行情。
        如果未传入 codes，则先获取所有 Listed 股票代码，再批量获取行情。

        Args:
            codes: 可选，股票代码列表（带交易所后缀，如 ["000001.SZ", "600000.SH"]）。

        Returns:
            List of dicts with keys: code, price, change_pct, change_amount,
            volume, amount, open, high, low, pre_close
        """
        if codes is None or len(codes) == 0:
            # 未指定 codes：先获取所有 Listed 股票代码
            logger.info("Tushare fetch_quote: 未指定 codes，自动获取全市场股票列表")
            basic_info = self.fetch_basic_info()
            # 转换为 Tushare ts_code 格式: 000001 -> 000001.SZ
            codes = []
            for item in basic_info:
                exchange = item.get("exchange", "")
                code = item.get("code", "")
                if exchange and code:
                    codes.append(f"{code}.{exchange}")
            if not codes:
                logger.warning("Tushare fetch_quote: 无法获取股票列表")
                return []

        logger.info("Tushare 获取实时行情，股票数: %d", len(codes))

        # Tushare rt_k 接口可能有数量限制，分批获取
        batch_size = 100
        all_records = []

        for i in range(0, len(codes), batch_size):
            batch = codes[i:i + batch_size]
            try:
                def _call():
                    return self._pro.rt_k(ts_code=",".join(batch))

                records = self._safe_call(f"fetch_quote_batch_{i}", _call)
                all_records.extend(records)
            except Exception as e:
                logger.warning("Tushare fetch_quote 批次 %d 失败: %s", i, str(e))

        result = []
        for row in all_records:
            ts_code = row.get("ts_code", "")
            code = ts_code.split(".")[0] if "." in ts_code else ts_code

            result.append({
                "code": code,
                "price": row.get("close"),
                "change_pct": row.get("pct_chg"),
                "change_amount": row.get("change"),
                "volume": row.get("vol"),  # 单位：手
                "amount": row.get("amount"),  # 单位：千元
                "open": row.get("open"),
                "high": row.get("high"),
                "low": row.get("low"),
                "pre_close": row.get("pre_close"),
            })

        logger.info("Tushare fetch_quote 完成，共 %d 条", len(result))
        return result

    def fetch_daily_quote(
        self,
        code: str,
        start_date: str,
        end_date: str,
        period: str = "daily",
    ) -> List[Dict[str, Any]]:
        """获取指定股票的历史日K线行情数据。

        Args:
            code: 股票代码（支持纯数字 "600132" 或带后缀 "600132.SH"）。
            start_date: 开始日期，格式 "YYYYMMDD" 或 "YYYY-MM-DD"。
            end_date: 结束日期，格式 "YYYYMMDD" 或 "YYYY-MM-DD"。
            period: 周期，默认为 "daily"。

        Returns:
            List of dicts with keys: code, trade_date, open, high, low, close,
            pre_close, vol, amount, pct_chg, period
        """
        # 兼容纯数字代码：自动添加交易所后缀
        ts_code = self._to_ts_code(code)

        # 兼容 YYYY-MM-DD 格式：转换为 YYYYMMDD
        sd = start_date.replace("-", "")
        ed = end_date.replace("-", "")

        logger.info(
            "Tushare 获取日K线: code=%s, start=%s, end=%s", ts_code, sd, ed
        )

        def _call():
            return self._pro.daily(
                ts_code=ts_code, start_date=sd, end_date=ed
            )

        records = self._safe_call("fetch_daily_quote", _call)

        result = []
        for row in records:
            result.append({
                "code": code.split(".")[0] if "." in code else code,
                "trade_date": row.get("trade_date"),
                "open": row.get("open"),
                "high": row.get("high"),
                "low": row.get("low"),
                "close": row.get("close"),
                "pre_close": row.get("pre_close"),
                "vol": row.get("vol"),
                "amount": row.get("amount"),
                "pct_chg": row.get("pct_chg"),
                "period": period,
            })

        logger.info("Tushare fetch_daily_quote 完成，共 %d 条", len(result))
        return result

    def fetch_financial(self, code: str) -> List[Dict[str, Any]]:
        """获取指定股票的财务指标数据。

        Args:
            code: 股票代码（带交易所后缀，如 "000001.SZ"）。

        Returns:
            List of dicts with keys: code, report_date, roe, net_profit,
            revenue, eps, gross_margin, debt_ratio
        """
        logger.info("Tushare 获取财务指标: code=%s", code)

        def _call():
            return self._pro.fina_indicator(ts_code=code)

        records = self._safe_call("fetch_financial", _call)

        result = []
        for row in records:
            result.append({
                "code": code.split(".")[0] if "." in code else code,
                "report_date": row.get("end_date"),
                "roe": row.get("roe"),
                "net_profit": row.get("n_profit"),
                "revenue": row.get("revenue"),
                "eps": row.get("basic_eps"),
                "gross_margin": row.get("gross_margin"),
                "debt_ratio": row.get("debt_ratio"),
            })

        logger.info("Tushare fetch_financial 完成，共 %d 条", len(result))
        return result
