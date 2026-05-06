"""BaoStock 数据源客户端。

BaoStock 是免费的 A 股数据接口，需要先 login 再查询，最后 logout。
获取基础信息、日K线、盈利数据等原始数据。
返回结果为 List[Dict]，后续由 data_cleaner 服务清洗后入库。

使用方式:
    client = BaoStockClient()
    stocks = client.fetch_basic_info()
    quotes = client.fetch_daily_quote("sh.600000", "2024-01-01", "2024-12-31")
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

import baostock as bs

logger = logging.getLogger(__name__)


class BaoStockClient:
    """BaoStock 数据源客户端。

    所有方法均为同步阻塞调用。每个方法内部独立管理 login/ logout 生命周期，
    使用 try/finally 确保 logout 一定会执行。
    错误时返回空列表并记录日志。
    """

    def __init__(self, username: str = "", password: str = "") -> None:
        """初始化 BaoStock 客户端。

        Args:
            username: 用户名，默认为空字符串（公开数据无需认证）。
            password: 密码，默认为空字符串（公开数据无需认证）。
        """
        self._username = username
        self._password = password
        logger.info("BaoStockClient 初始化完成")

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    def _login(self) -> bool:
        """登录 BaoStock。

        Returns:
            登录是否成功。
        """
        try:
            # BaoStock 公开数据无需认证，无参调用即可
            if self._username:
                lg = bs.login(user_id=self._username, password=self._password)
            else:
                lg = bs.login()
            if lg.error_code != "0":
                logger.error("BaoStock 登录失败: error_code=%s, error_msg=%s", lg.error_code, lg.error_msg)
                return False
            logger.debug("BaoStock 登录成功")
            return True
        except Exception as e:
            logger.error("BaoStock 登录异常: %s", str(e), exc_info=True)
            return False

    def _logout(self) -> None:
        """登出 BaoStock。"""
        try:
            bs.logout()
            logger.debug("BaoStock 登出成功")
        except Exception as e:
            logger.warning("BaoStock 登出异常: %s", str(e))

    @staticmethod
    def _query_to_dicts(rs) -> List[Dict[str, Any]]:
        """将 BaoStock 查询结果转换为 list[dict]。

        Args:
            rs: BaoStock 查询结果对象（OutSet）。

        Returns:
            记录列表。如果查询出错，返回空列表。
        """
        if rs is None:
            return []

        # 检查是否有错误
        if hasattr(rs, "error_code") and rs.error_code != "0":
            error_msg = getattr(rs, "error_msg", "未知错误")
            logger.error("BaoStock 查询错误: error_code=%s, error_msg=%s", rs.error_code, error_msg)
            return []

        data_list = []
        try:
            while (rs.error_code == "0") and rs.next():
                data_list.append(rs.get_row_data())
        except Exception as e:
            logger.error("BaoStock 遍历结果异常: %s", str(e))
            return []

        fields = rs.fields
        result = []
        for row in data_list:
            record = {}
            for i, field in enumerate(fields):
                if i < len(row):
                    record[field] = row[i]
                else:
                    record[field] = None
            result.append(record)

        return result

    def _safe_query(self, method_name: str, query_func) -> List[Dict[str, Any]]:
        """安全查询包装器：login -> query -> logout。

        Args:
            method_name: 方法名称（用于日志）
            query_func: 在 login 后执行的查询函数，应返回 BaoStock OutSet 对象。

        Returns:
            查询结果的 list[dict]，异常或错误时返回空列表。
        """
        if not self._login():
            logger.error("BaoStock %s 登录失败", method_name)
            return []

        try:
            rs = query_func()
            records = self._query_to_dicts(rs)
            logger.info("BaoStock %s 成功，获取 %d 条记录", method_name, len(records))
            return records
        except Exception as e:
            logger.error("BaoStock %s 查询异常: %s", method_name, str(e), exc_info=True)
            return []
        finally:
            self._logout()

    # ------------------------------------------------------------------
    # 公开方法
    # ------------------------------------------------------------------

    def fetch_basic_info(self) -> List[Dict[str, Any]]:
        """获取所有股票的基础信息。

        使用 bs.query_stock_basic(code="") 获取全市场股票。

        Returns:
            List of dicts with keys: code, name, industry, list_date
        """
        logger.info("BaoStock 获取股票基础信息...")

        def _query():
            return bs.query_stock_basic(code="")

        records = self._safe_query("fetch_basic_info", _query)

        result = []
        for row in records:
            code = row.get("code", "")
            # BaoStock 的 code 格式为 "sh.600000" 或 "sz.000001"
            pure_code = code.split(".")[-1] if "." in code else code

            result.append({
                "code": pure_code,
                "name": row.get("code_name", ""),
                "industry": row.get("industry"),
                "list_date": row.get("ipoDate"),
                "exchange": row.get("code", "")[:2].upper() if "." in code else "",
            })

        logger.info("BaoStock fetch_basic_info 完成，共 %d 条", len(result))
        return result

    def fetch_daily_quote(
        self,
        code: str,
        start_date: str,
        end_date: str,
        period: str = "daily",
    ) -> List[Dict[str, Any]]:
        """获取指定股票的历史K线行情数据。

        使用 bs.query_history_k_data_plus() 获取历史K线。

        Args:
            code: 股票代码（BaoStock 格式，如 "sh.600000" 或纯数字 "600000"）。
                  如果传入纯数字，会自动添加前缀。
            start_date: 开始日期，格式 "YYYY-MM-DD"。
            end_date: 结束日期，格式 "YYYY-MM-DD"。
            period: 周期，"daily"（日线）/"weekly"（周线）/"monthly"（月线）。

        Returns:
            List of dicts with keys: code, trade_date, open, high, low, close,
            volume, amount, period
        """
        # 确保 code 格式为 BaoStock 格式（sh.600000 或 sz.000001）
        bs_code = self._to_baostock_code(code)

        # BaoStock 使用 "YYYY-MM-DD" 格式，兼容 "YYYYMMDD" 输入
        bs_start = self._normalize_date(start_date)
        bs_end = self._normalize_date(end_date)

        # frequency 映射: daily->d, weekly->w, monthly->m
        bs_freq_map = {"daily": "d", "weekly": "w", "monthly": "m"}
        frequency = bs_freq_map.get(period, "d")

        logger.info(
            "BaoStock 获取K线: code=%s, start=%s, end=%s, period=%s, freq=%s",
            bs_code, bs_start, bs_end, period, frequency,
        )

        def _query():
            return bs.query_history_k_data_plus(
                bs_code,
                "date,open,high,low,close,volume,amount",
                start_date=bs_start,
                end_date=bs_end,
                frequency=frequency,
                adjustflag="2",  # 前复权
            )

        records = self._safe_query("fetch_daily_quote", _query)

        pure_code = code.split(".")[-1] if "." in code else code

        result = []
        for row in records:
            result.append({
                "code": pure_code,
                "trade_date": row.get("date"),
                "open": row.get("open"),
                "high": row.get("high"),
                "low": row.get("low"),
                "close": row.get("close"),
                "volume": row.get("volume"),
                "amount": row.get("amount"),
                "pre_close": None,  # BaoStock 此接口不返回昨收
                "pct_chg": None,  # 可从数据计算
                "period": period,
            })

        logger.info("BaoStock fetch_daily_quote 完成，共 %d 条", len(result))
        return result

    def fetch_financial(self, code: str) -> List[Dict[str, Any]]:
        """获取指定股票的盈利数据。

        使用 bs.query_profit_data() 获取最近 4 个季度的盈利数据。

        Args:
            code: 股票代码（BaoStock 格式或纯数字）。

        Returns:
            List of dicts with keys: code, report_date, roe, net_profit,
            revenue, eps
        """
        bs_code = self._to_baostock_code(code)
        pure_code = code.split(".")[-1] if "." in code else code

        logger.info("BaoStock 获取财务数据: code=%s", bs_code)

        # 获取最近 4 个季度的数据（当前年份及上一年）
        current_year = datetime.now().year
        quarters_to_fetch = []

        # 构造最近 4 个季度的 (year, quarter) 组合
        for year in range(current_year, current_year - 3, -1):
            for quarter in range(4, 0, -1):
                quarters_to_fetch.append((year, quarter))
                if len(quarters_to_fetch) >= 4:
                    break
            if len(quarters_to_fetch) >= 4:
                break

        all_records = []
        for year, quarter in quarters_to_fetch:
            if not self._login():
                logger.error("BaoStock fetch_financial 登录失败")
                break

            try:
                rs = bs.query_profit_data(code=bs_code, year=year, quarter=quarter)
                records = self._query_to_dicts(rs)
                if records:
                    all_records.extend(records)
            except Exception as e:
                logger.warning(
                    "BaoStock query_profit_data year=%d quarter=%d 异常: %s",
                    year, quarter, str(e),
                )
            finally:
                self._logout()

        result = []
        for row in all_records:
            result.append({
                "code": pure_code,
                "report_date": row.get("statDate"),
                "roe": row.get("roeAvg"),
                "net_profit": row.get("npPerShare"),
                "revenue": row.get("netProfit"),
                "eps": row.get("epsTTM"),
                "gross_margin": row.get("grossProfitMargin"),
                "debt_ratio": row.get("debtRatio"),
            })

        logger.info("BaoStock fetch_financial 完成，共 %d 条", len(result))
        return result

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_date(date_str: str) -> str:
        """将日期字符串标准化为 YYYY-MM-DD 格式。

        Args:
            date_str: 日期字符串，支持 "YYYYMMDD" 或 "YYYY-MM-DD" 格式。

        Returns:
            YYYY-MM-DD 格式的日期字符串。
        """
        if not date_str:
            return date_str
        # 已经是 YYYY-MM-DD 格式
        if "-" in date_str:
            return date_str
        # YYYYMMDD -> YYYY-MM-DD
        if len(date_str) == 8 and date_str.isdigit():
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        return date_str

    @staticmethod
    def _to_baostock_code(code: str) -> str:
        """将股票代码转换为 BaoStock 格式。

        Args:
            code: 股票代码，支持 "sh.600000"、"600000"、"000001.SZ" 等格式。

        Returns:
            BaoStock 格式的代码，如 "sh.600000"。
        """
        # 已经是 BaoStock 格式（sh.xxx 或 sz.xxx）
        if "." in code:
            parts = code.split(".")
            prefix = parts[0].lower()
            num = parts[1]
            if prefix in ("sh", "sz"):
                return code.lower()
            # Tushare 格式: 600000.SH -> sh.600000
            if prefix.isdigit() and len(prefix) == 6:
                return f"{prefix}.{num.lower()}"
            # 尝试根据数字部分判断
            num_str = parts[0] if parts[0].isdigit() else parts[1]
            if num_str.startswith("6"):
                return f"sh.{num_str}"
            else:
                return f"sz.{num_str}"

        # 纯数字代码
        if code.startswith("6"):
            return f"sh.{code}"
        else:
            return f"sz.{code}"
