"""金融数据工具集 — 数据库优先 + 新浪财经降级"""

import json
import logging
import time
from typing import Any, List, Optional

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# 超时重试配置
MAX_RETRIES = 2
RETRY_DELAY = 1  # 秒

# === 行情缓存（避免每次拉全市场数据） ===
_spot_cache: dict | None = None
_spot_cache_time: float = 0
_SPOT_CACHE_TTL = 300  # 5分钟缓存


# ============================================================
# 同步数据库引擎 — 用于从 MySQL 读取已同步的股票数据
# ============================================================

_sync_engine = None
_sync_session_factory = None


def _get_sync_engine():
    """获取同步 SQLAlchemy 引擎（懒加载，全局单例）。"""
    global _sync_engine, _sync_session_factory
    if _sync_engine is None:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from app.core.config import settings

        # 将 mysql+aiomysql:// 转换为 mysql+pymysql://
        url = settings.database_url
        if url.startswith("mysql+aiomysql://"):
            url = url.replace("mysql+aiomysql://", "mysql+pymysql://")
        elif url.startswith("mysql+asyncmy://"):
            url = url.replace("mysql+asyncmy://", "mysql+pymysql://")

        _sync_engine = create_engine(url, pool_size=5, max_overflow=10)
        _sync_session_factory = sessionmaker(bind=_sync_engine)
        logger.info("[DB] 同步数据库引擎初始化完成")
    return _sync_engine, _sync_session_factory


def _get_tushare_token() -> Optional[str]:
    """从数据库获取 Tushare Token（同步版本）。"""
    try:
        from cryptography.fernet import Fernet, InvalidToken
        from app.core.config import settings
        from app.infrastructure.db.models import DataSourceConfigModel

        engine, factory = _get_sync_engine()
        with factory() as session:
            stmt = session.query(DataSourceConfigModel).filter(
                DataSourceConfigModel.source_type == "tushare",
                DataSourceConfigModel.is_enabled == True,
            ).first()

            if not stmt or not stmt.api_key:
                logger.debug("[Tushare] 未配置 Tushare Token")
                return None

            encrypted_key = stmt.api_key
            # 解密
            key = settings.datasource_encryption_key or ""
            if key:
                try:
                    fernet = Fernet(key.encode())
                    return fernet.decrypt(encrypted_key.encode()).decode()
                except InvalidToken:
                    # 可能为旧明文数据
                    return encrypted_key
            else:
                # 未配置加密密钥，直接返回
                return encrypted_key
    except Exception as e:
        logger.warning("[Tushare] 获取 Token 失败: %s", e)
        return None


def _to_ts_code(code: str) -> str:
    """将纯数字股票代码转换为 Tushare ts_code 格式。"""
    if "." in code:
        return code
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


def _prefix_code_sina(code: str) -> str:
    """将纯数字代码转为新浪格式，如 600519 -> sh600519。"""
    if code.startswith(("sh", "sz")):
        return code
    if code.startswith("6"):
        return f"sh{code}"
    return f"sz{code}"


def _sina_history(code: str, days: int = 60) -> Optional[List[dict]]:
    """通过新浪财经获取历史日K线数据（同步 HTTP 调用）。"""
    try:
        import re as _re
        import httpx

        prefixed = _prefix_code_sina(code)
        url = (
            f"https://quotes.sina.cn/cn/api/jsonp_v2.php/var%20data"
            f"/CN_MarketDataService.getKLineData"
            f"?symbol={prefixed}&scale=240&datalen={days}"
        )
        headers = {"Referer": "https://finance.sina.com"}

        with httpx.Client(timeout=10) as client:
            resp = client.get(url, headers=headers)
            resp.raise_for_status()
            text = resp.text

        # JSONP 解析
        text = _re.sub(r"^/\*<script>.*?</script>\*/", "", text.strip(), flags=_re.DOTALL)
        match = _re.search(r"\((\[.*\])\)", text, _re.DOTALL)
        if not match:
            logger.warning("[新浪K线] JSONP解析失败 code=%s", code)
            return None

        items = json.loads(match.group(1))
        if not isinstance(items, list) or not items:
            return None

        result = []
        for item in items:
            day_str = item.get("day", "")
            trade_date = day_str.split(" ")[0] if " " in day_str else day_str
            result.append({
                "日期": trade_date,
                "开盘": str(item.get("open", "")),
                "最高": str(item.get("high", "")),
                "最低": str(item.get("low", "")),
                "收盘": str(item.get("close", "")),
                "前收盘": "",
                "成交量": str(item.get("volume", "")),
                "成交额": str(item.get("amount", "")) if item.get("amount") else "",
                "涨跌幅": "",
                "data_source": "sina",
            })

        logger.info("[新浪K线] 获取成功 code=%s count=%d", code, len(result))
        return result
    except Exception as e:
        logger.warning("[新浪K线] 获取失败 code=%s: %s", code, e)
        return None


def _query_db_quote(code: str) -> Optional[dict]:
    """从数据库查询最新行情数据。

    Args:
        code: 股票代码（纯数字）。

    Returns:
        dict 格式的行情数据，无数据时返回 None。
    """
    try:
        _, factory = _get_sync_engine()
        from app.infrastructure.db.models import MarketQuoteModel

        with factory() as session:
            # 按 quote_time 降序取最新一条
            result = (
                session.query(MarketQuoteModel)
                .filter(MarketQuoteModel.code == code)
                .order_by(MarketQuoteModel.quote_time.desc())
                .first()
            )
            if result is None:
                return None

            return {
                "code": result.code,
                "price": str(result.price) if result.price else "",
                "change_pct": str(result.change_pct) if result.change_pct else "",
                "change_amount": str(result.change_amount) if result.change_amount else "",
                "volume": str(result.volume) if result.volume else "",
                "amount": str(result.amount) if result.amount else "",
                "open": str(result.open_price) if result.open_price else "",
                "high": str(result.high_price) if result.high_price else "",
                "low": str(result.low_price) if result.low_price else "",
                "pre_close": str(result.pre_close) if result.pre_close else "",
                "quote_time": str(result.quote_time) if result.quote_time else "",
                "data_source": result.data_source,
            }
    except Exception as e:
        logger.warning("[DB查询] 行情数据查询失败: %s", e)
        return None


def _query_db_history(code: str, days: int = 60) -> Optional[List[dict]]:
    """从数据库查询历史K线数据。

    Args:
        code: 股票代码（纯数字）。
        days: 获取最近多少天的数据。

    Returns:
        list[dict] 格式的K线数据列表，无数据时返回 None。
    """
    try:
        _, factory = _get_sync_engine()
        from app.infrastructure.db.models import StockDailyQuoteModel
        from datetime import date, timedelta

        cutoff = date.today() - timedelta(days=days * 2)  # 放宽范围

        with factory() as session:
            results = (
                session.query(StockDailyQuoteModel)
                .filter(
                    StockDailyQuoteModel.code == code,
                    StockDailyQuoteModel.trade_date >= cutoff,
                )
                .order_by(StockDailyQuoteModel.trade_date.asc())
                .limit(days)
                .all()
            )
            if not results:
                return None

            return [
                {
                    "日期": str(r.trade_date),
                    "开盘": str(r.open_price) if r.open_price else "",
                    "最高": str(r.high_price) if r.high_price else "",
                    "最低": str(r.low_price) if r.low_price else "",
                    "收盘": str(r.close_price) if r.close_price else "",
                    "前收盘": str(r.pre_close) if r.pre_close else "",
                    "成交量": str(r.volume) if r.volume else "",
                    "成交额": str(r.amount) if r.amount else "",
                    "涨跌幅": str(r.pct_chg) if r.pct_chg else "",
                    "data_source": r.data_source,
                }
                for r in results
            ]
    except Exception as e:
        logger.warning("[DB查询] 历史K线数据查询失败: %s", e)
        return None


def _query_db_financial(code: str) -> Optional[List[dict]]:
    """从数据库查询财务数据。

    Args:
        code: 股票代码（纯数字）。

    Returns:
        list[dict] 格式的财务数据列表，无数据时返回 None。
    """
    try:
        _, factory = _get_sync_engine()
        from app.infrastructure.db.models import StockFinancialModel

        with factory() as session:
            results = (
                session.query(StockFinancialModel)
                .filter(StockFinancialModel.code == code)
                .order_by(StockFinancialModel.report_date.desc())
                .limit(4)
                .all()
            )
            if not results:
                return None

            return [
                {
                    "报告日期": str(r.report_date),
                    "ROE": str(r.roe) if r.roe else "",
                    "净利润": str(r.net_profit) if r.net_profit else "",
                    "营业收入": str(r.revenue) if r.revenue else "",
                    "每股收益": str(r.eps) if r.eps else "",
                    "毛利率": str(r.gross_margin) if r.gross_margin else "",
                    "资产负债率": str(r.debt_ratio) if r.debt_ratio else "",
                    "data_source": r.data_source,
                }
                for r in results
            ]
    except Exception as e:
        logger.warning("[DB查询] 财务数据查询失败: %s", e)
        return None


# ============================================================
# Tushare 降级调用
# ============================================================

def _tushare_quote(code: str) -> Optional[dict]:
    """通过 Tushare 获取实时行情（单只股票）。"""
    try:
        import tushare as ts

        token = _get_tushare_token()
        if not token:
            logger.debug("[Tushare] Token 未配置")
            return None

        ts.set_token(token)
        pro = ts.pro_api()

        ts_code = _to_ts_code(code)
        df = pro.rt_k(ts_code=ts_code)
        if df is None or df.empty:
            logger.debug("[Tushare] rt_k 返回空: %s", ts_code)
            return None

        row = df.iloc[0]
        return {
            "code": code,
            "price": row.get("close", ""),
            "change_pct": row.get("pct_chg", ""),
            "change_amount": row.get("change", ""),
            "volume": row.get("vol", ""),
            "amount": row.get("amount", ""),
            "open": row.get("open", ""),
            "high": row.get("high", ""),
            "low": row.get("low", ""),
            "pre_close": row.get("pre_close", ""),
        }
    except Exception as e:
        logger.warning("[Tushare] 实时行情获取失败: %s", e)
        return None


def _tushare_history(code: str, days: int = 60) -> Optional[List[dict]]:
    """通过 Tushare 获取历史日K线数据。"""
    try:
        import tushare as ts
        from datetime import date, timedelta

        token = _get_tushare_token()
        if not token:
            return None

        ts.set_token(token)
        pro = ts.pro_api()

        ts_code = _to_ts_code(code)
        start_date = (date.today() - timedelta(days=days * 2)).strftime("%Y%m%d")
        end_date = date.today().strftime("%Y%m%d")

        df = pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
        if df is None or df.empty:
            return None

        df = df.head(days)
        records = df.to_dict(orient="records")
        return [
            {
                "日期": str(r.get("trade_date", "")),
                "开盘": str(r.get("open", "")),
                "最高": str(r.get("high", "")),
                "最低": str(r.get("low", "")),
                "收盘": str(r.get("close", "")),
                "前收盘": str(r.get("pre_close", "")),
                "成交量": str(r.get("vol", "")),
                "成交额": str(r.get("amount", "")),
                "涨跌幅": str(r.get("pct_chg", "")),
                "data_source": "tushare",
            }
            for r in records
        ]
    except Exception as e:
        logger.warning("[Tushare] 历史K线获取失败: %s", e)
        return None


def _tushare_financial(code: str) -> Optional[List[dict]]:
    """通过 Tushare 获取财务指标数据。"""
    try:
        import tushare as ts

        token = _get_tushare_token()
        if not token:
            return None

        ts.set_token(token)
        pro = ts.pro_api()

        ts_code = _to_ts_code(code)
        df = pro.fina_indicator(ts_code=ts_code)
        if df is None or df.empty:
            return None

        df = df.head(4)  # 最近4个报告期
        records = df.to_dict(orient="records")
        return [
            {
                "报告日期": str(r.get("end_date", "")),
                "ROE": str(r.get("roe", "")),
                "净利润": str(r.get("n_profit", "")),
                "营业收入": str(r.get("revenue", "")),
                "每股收益": str(r.get("basic_eps", "")),
                "毛利率": str(r.get("gross_margin", "")),
                "资产负债率": str(r.get("debt_ratio", "")),
                "data_source": "tushare",
            }
            for r in records
        ]
    except Exception as e:
        logger.warning("[Tushare] 财务数据获取失败: %s", e)
        return None


# ============================================================
# 重试辅助
# ============================================================

def _retry_call(func, *args, retries=MAX_RETRIES, delay=RETRY_DELAY):
    """带重试的函数调用"""
    last_error = None
    for attempt in range(retries + 1):
        try:
            return func(*args)
        except Exception as e:
            last_error = e
            if attempt < retries:
                logger.warning("[重试] %s 第%d次失败: %s，%ds后重试", func.__name__, attempt + 1, e, delay)
                import time as _time
                _time.sleep(delay)
    raise last_error


# === 工具函数实现 ===

def _fetch_stock_quote(stock_code: str) -> str:
    """获取股票实时/最新行情数据（数据库优先 + Tushare 降级 + BaoStock 保底）"""
    t0 = time.time()

    # === 1. 优先从数据库查询 ===
    db_data = _query_db_quote(stock_code)
    if db_data:
        logger.info("[耗时] _fetch_stock_quote(DB命中): %.3fs, code=%s", time.time() - t0, stock_code)
        logger.info("[fetch_stock_quote] 数据库命中: code=%s, source=%s", stock_code, db_data.get("data_source"))
        result = {
            "代码": stock_code,
            "最新价": db_data["price"],
            "涨跌幅": db_data["change_pct"],
            "涨跌额": db_data["change_amount"],
            "成交量": db_data["volume"],
            "成交额": db_data["amount"],
            "最高": db_data["high"],
            "最低": db_data["low"],
            "今开": db_data["open"],
            "昨收": db_data["pre_close"],
            "更新时间": db_data["quote_time"],
            "数据来源": f"数据库({db_data['data_source']})",
        }
        return json.dumps(result, ensure_ascii=False, indent=2)

    logger.info("[fetch_stock_quote] 数据库无数据，尝试 Tushare: code=%s", stock_code)

    # === 2. Tushare 查询 ===
    tushare_data = _tushare_quote(stock_code)
    if tushare_data:
        logger.info("[耗时] _fetch_stock_quote(Tushare): %.3fs, code=%s", time.time() - t0, stock_code)
        result = {
            "代码": stock_code,
            "最新价": str(tushare_data["price"]),
            "涨跌幅": str(tushare_data["change_pct"]),
            "涨跌额": str(tushare_data["change_amount"]),
            "成交量": str(tushare_data["volume"]),
            "成交额": str(tushare_data["amount"]),
            "最高": str(tushare_data["high"]),
            "最低": str(tushare_data["low"]),
            "今开": str(tushare_data["open"]),
            "昨收": str(tushare_data["pre_close"]),
            "数据来源": "Tushare",
        }
        return json.dumps(result, ensure_ascii=False, indent=2)

    logger.info("[fetch_stock_quote] Tushare 不可用，尝试 BaoStock 降级")

    # === 3. BaoStock 降级 ===
    try:
        import baostock as bs
        lg = bs.login()
        if lg.error_code != '0':
            return f"未找到股票 {stock_code} 的行情数据（数据库无数据，Tushare不可用，BaoStock登录失败）"

        prefix = "sh" if stock_code.startswith(("6", "9")) else "sz"
        rs = bs.query_history_k_data_plus(
            f"{prefix}.{stock_code}",
            "date,code,open,high,low,close,volume,amount,turn,pctChg",
            start_date="", end_date="",
            frequency="d", adjustflag="2"
        )

        if rs.error_code != '0':
            bs.logout()
            return f"未找到股票 {stock_code} 的行情数据（数据库无数据，Tushare不可用，BaoStock查询失败: {rs.error_msg}）"

        rows = []
        while (rs.error_code == '0') and rs.next():
            rows.append(rs.get_row_data())

        bs.logout()

        if not rows:
            return f"未找到股票代码 {stock_code} 的行情数据（数据库无数据，Tushare不可用，BaoStock无数据）"

        last_row = rows[-1]
        result = {
            "代码": stock_code,
            "名称": f"{stock_code}(BaoStock)",
            "最新价": last_row[5] if len(last_row) > 5 else "",
            "今开": last_row[2] if len(last_row) > 2 else "",
            "最高": last_row[3] if len(last_row) > 3 else "",
            "最低": last_row[4] if len(last_row) > 4 else "",
            "成交量": last_row[6] if len(last_row) > 6 else "",
            "涨跌幅": last_row[9] if len(last_row) > 9 else "",
            "换手率": last_row[8] if len(last_row) > 8 else "",
            "数据来源": "BaoStock(保底)",
        }
        return json.dumps(result, ensure_ascii=False, indent=2)
    except ImportError:
        return f"未找到股票 {stock_code} 的行情数据：数据库无数据，Tushare不可用，BaoStock未安装"
    except Exception as e2:
        return f"获取行情数据失败: 数据库无数据，Tushare不可用，BaoStock({e2})"


def _fetch_stock_history(stock_code: str, period: str = "daily", days: int = 60) -> str:
    """获取股票历史K线数据（数据库优先 + 新浪财经降级）"""
    t0 = time.time()

    # === 1. 优先从数据库查询 ===
    db_data = _query_db_history(stock_code, days)
    if db_data:
        logger.info("[耗时] _fetch_stock_history(DB命中): %.3fs, code=%s", time.time() - t0, stock_code)
        logger.info("[fetch_stock_history] 数据库命中: code=%s, 共 %d 条, source=%s",
                     stock_code, len(db_data), db_data[0].get("data_source"))
        return json.dumps(db_data, ensure_ascii=False, indent=2)

    logger.info("[fetch_stock_history] 数据库无数据，尝试新浪财经: code=%s", stock_code)

    # === 2. 新浪财经查询 ===
    sina_data = _sina_history(stock_code, days)
    if sina_data:
        logger.info("[耗时] _fetch_stock_history(新浪): %.3fs, code=%s", time.time() - t0, stock_code)
        return json.dumps(sina_data, ensure_ascii=False, indent=2)

    # === 3. 都不可用 ===
    return f"未找到股票代码 {stock_code} 的历史数据（数据库和新浪均无数据，请确认已同步数据）"


def _fetch_stock_financial(stock_code: str) -> str:
    """获取股票财务指标数据（数据库优先 + Tushare 降级）"""
    t0 = time.time()

    # === 1. 优先从数据库查询 ===
    db_data = _query_db_financial(stock_code)
    if db_data:
        logger.info("[耗时] _fetch_stock_financial(DB命中): %.3fs, code=%s", time.time() - t0, stock_code)
        logger.info("[fetch_stock_financial] 数据库命中: code=%s, 共 %d 条, source=%s",
                     stock_code, len(db_data), db_data[0].get("data_source"))
        return json.dumps(db_data, ensure_ascii=False, indent=2)

    logger.info("[fetch_stock_financial] 数据库无数据，尝试 Tushare: code=%s", stock_code)

    # === 2. Tushare 查询 ===
    tushare_data = _tushare_financial(stock_code)
    if tushare_data:
        logger.info("[耗时] _fetch_stock_financial(Tushare): %.3fs, code=%s", time.time() - t0, stock_code)
        return json.dumps(tushare_data, ensure_ascii=False, indent=2)

    # === 3. 都不可用 ===
    return f"未找到股票代码 {stock_code} 的财务数据（数据库和Tushare均无数据，请确认已同步数据）"


def _fetch_stock_news(stock_code: str) -> str:
    """获取个股最新新闻/公告数据

    注意: Tushare 暂无好用的新闻接口，此处保留 AKShare 作为唯一来源。
    如果 AKShare 不可用，则返回提示信息。
    """
    t0 = time.time()
    try:
        import akshare as ak

        # 获取个股新闻
        df = ak.stock_news_em(symbol=stock_code)
        if df.empty:
            return f"未找到股票代码 {stock_code} 的新闻数据"

        df = df.head(10)  # 最近10条
        records = df.to_dict(orient="records")
        for record in records:
            for key in record:
                record[key] = str(record[key])

        logger.info("[耗时] _fetch_stock_news: %.3fs, code=%s", time.time() - t0, stock_code)
        return json.dumps(records, ensure_ascii=False, indent=2)
    except ImportError:
        return "AKShare 未安装，无法获取新闻数据"
    except Exception as e:
        logger.warning("[fetch_stock_news] 获取新闻数据失败: %s", e)
        return f"获取新闻数据失败: {e}（AKShare调用出错，新闻数据不可用）"


# === LangChain Tool 定义 ===

@tool
def get_stock_quote(stock_code: str) -> str:
    """获取A股股票的最新实时行情数据，包括价格、涨跌幅、成交量、市盈率等。

    Args:
        stock_code: 股票代码，如 "000001"

    Returns:
        JSON 格式的行情数据
    """
    return _fetch_stock_quote(stock_code)


@tool
def get_stock_history(stock_code: str, period: str = "daily", days: int = 60) -> str:
    """获取A股股票的历史K线数据。

    Args:
        stock_code: 股票代码，如 "000001"
        period: 周期，可选 "daily"(日线), "weekly"(周线), "monthly"(月线)，默认 "daily"
        days: 获取最近多少天的数据，默认60天

    Returns:
        JSON 格式的历史K线数据列表
    """
    return _fetch_stock_history(stock_code, period, days)


@tool
def get_stock_financial(stock_code: str) -> str:
    """获取A股股票的财务指标数据（基本面），包括营收、利润、ROE等。

    Args:
        stock_code: 股票代码，如 "000001"

    Returns:
        JSON 格式的财务指标数据
    """
    return _fetch_stock_financial(stock_code)


@tool
def get_stock_news(stock_code: str) -> str:
    """获取A股股票的最新新闻和公告数据。

    Args:
        stock_code: 股票代码，如 "000001"

    Returns:
        JSON 格式的新闻数据列表
    """
    return _fetch_stock_news(stock_code)


# === 工具注册 ===

# 工具名到执行函数的映射（供节点手动调用使用）
TOOL_FUNCTION_MAP: dict[str, Any] = {
    "get_stock_quote": _fetch_stock_quote,
    "get_stock_history": _fetch_stock_history,
    "get_stock_financial": _fetch_stock_financial,
    "get_stock_news": _fetch_stock_news,
}


def get_stock_tools() -> list:
    """返回所有股票数据工具列表（LangChain Tool 格式）"""
    return [get_stock_quote, get_stock_history, get_stock_financial, get_stock_news]


def get_stock_tools_schema() -> list[dict]:
    """返回所有股票数据工具的 JSON Schema（OpenAI function calling 格式）"""
    import langchain_core.utils.function_calling as fc

    tools = get_stock_tools()
    schemas = []
    for t in tools:
        schema = fc.convert_to_openai_tool(t)
        schemas.append(schema)
    return schemas
