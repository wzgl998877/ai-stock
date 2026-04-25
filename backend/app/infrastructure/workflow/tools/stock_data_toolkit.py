"""金融数据工具集 — 数据库优先 + AKShare 降级（含 BaoStock 降级 + 超时重试 + 缓存）"""

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
# 重试 & 缓存辅助
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


def _get_spot_df():
    """获取全市场行情 DataFrame（带缓存，5分钟TTL）"""
    global _spot_cache, _spot_cache_time

    now = time.time()
    if _spot_cache is not None and (now - _spot_cache_time) < _SPOT_CACHE_TTL:
        return _spot_cache

    import akshare as ak
    df = ak.stock_zh_a_spot_em()
    _spot_cache = df
    _spot_cache_time = now
    logger.info("[行情缓存] 刷新，共 %d 条", len(df))
    return df


# === 工具函数实现 ===

def _fetch_stock_quote(stock_code: str) -> str:
    """获取股票实时/最新行情数据（数据库优先 + AKShare 降级）"""
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

    logger.info("[fetch_stock_quote] 数据库无数据，尝试 AKShare: code=%s", stock_code)

    # === 2. AKShare 查询 ===
    try:
        import akshare as ak

        # 优先使用缓存的全市场行情
        try:
            df = _get_spot_df()
            row = df[df["代码"] == stock_code]
            if not row.empty:
                r = row.iloc[0]
                result = {
                    "代码": str(r.get("代码", "")),
                    "名称": str(r.get("名称", "")),
                    "最新价": str(r.get("最新价", "")),
                    "涨跌幅": str(r.get("涨跌幅", "")),
                    "涨跌额": str(r.get("涨跌额", "")),
                    "成交量": str(r.get("成交量", "")),
                    "成交额": str(r.get("成交额", "")),
                    "振幅": str(r.get("振幅", "")),
                    "最高": str(r.get("最高", "")),
                    "最低": str(r.get("最低", "")),
                    "今开": str(r.get("今开", "")),
                    "昨收": str(r.get("昨收", "")),
                    "量比": str(r.get("量比", "")),
                    "换手率": str(r.get("换手率", "")),
                    "市盈率-动态": str(r.get("市盈率-动态", "")),
                    "市净率": str(r.get("市净率", "")),
                    "总市值": str(r.get("总市值", "")),
                    "流通市值": str(r.get("流通市值", "")),
                }
                logger.info("[耗时] _fetch_stock_quote(AKShare): %.3fs, code=%s", time.time() - t0, stock_code)
                return json.dumps(result, ensure_ascii=False, indent=2)
        except Exception as cache_err:
            logger.warning("[fetch_stock_quote] 缓存读取失败，降级到直接查询: %s", cache_err)
            global _spot_cache
            _spot_cache = None
    except ImportError:
        logger.warning("[fetch_stock_quote] AKShare 未安装，尝试 BaoStock")
    except Exception as e:
        logger.error("[fetch_stock_quote] AKShare获取行情数据失败: %s，尝试BaoStock降级", e)

    # === 3. BaoStock 降级 ===
    try:
        import baostock as bs
        lg = bs.login()
        if lg.error_code != '0':
            return f"未找到股票 {stock_code} 的行情数据（数据库无数据，AKShare不可用，BaoStock登录失败）"

        prefix = "sh" if stock_code.startswith(("6", "9")) else "sz"
        rs = bs.query_history_k_data_plus(
            f"{prefix}.{stock_code}",
            "date,code,open,high,low,close,volume,amount,turn,pctChg",
            start_date="", end_date="",
            frequency="d", adjustflag="2"
        )

        if rs.error_code != '0':
            bs.logout()
            return f"未找到股票 {stock_code} 的行情数据（数据库无数据，AKShare不可用，BaoStock查询失败: {rs.error_msg}）"

        rows = []
        while (rs.error_code == '0') and rs.next():
            rows.append(rs.get_row_data())

        bs.logout()

        if not rows:
            return f"未找到股票代码 {stock_code} 的行情数据（数据库无数据，AKShare不可用，BaoStock无数据）"

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
            "数据来源": "BaoStock(降级)",
        }
        return json.dumps(result, ensure_ascii=False, indent=2)
    except ImportError:
        return f"未找到股票 {stock_code} 的行情数据：数据库无数据，AKShare未安装，BaoStock未安装"
    except Exception as e2:
        return f"获取行情数据失败: 数据库无数据，AKShare不可用，BaoStock({e2})"


def _fetch_stock_history(stock_code: str, period: str = "daily", days: int = 60) -> str:
    """获取股票历史K线数据（数据库优先 + AKShare 降级）"""
    t0 = time.time()

    # === 1. 优先从数据库查询 ===
    db_data = _query_db_history(stock_code, days)
    if db_data:
        logger.info("[耗时] _fetch_stock_history(DB命中): %.3fs, code=%s", time.time() - t0, stock_code)
        logger.info("[fetch_stock_history] 数据库命中: code=%s, 共 %d 条, source=%s",
                     stock_code, len(db_data), db_data[0].get("data_source"))
        return json.dumps(db_data, ensure_ascii=False, indent=2)

    logger.info("[fetch_stock_history] 数据库无数据，尝试 AKShare: code=%s", stock_code)

    # === 2. AKShare 查询 ===
    try:
        import akshare as ak

        df = ak.stock_zh_a_hist(symbol=stock_code, period=period, adjust="qfq")
        if df.empty:
            return f"未找到股票代码 {stock_code} 的历史数据（数据库和AKShare均无数据）"

        # 只取最近 days 天
        df = df.tail(days)
        records = df.to_dict(orient="records")
        # 转换值为字符串以确保 JSON 可序列化
        for record in records:
            for key in record:
                record[key] = str(record[key])

        logger.info("[耗时] _fetch_stock_history(AKShare): %.3fs, code=%s", time.time() - t0, stock_code)
        return json.dumps(records, ensure_ascii=False, indent=2)
    except ImportError:
        return "AKShare 未安装，无法获取历史数据（数据库也无数据）"
    except Exception as e:
        logger.error("[fetch_stock_history] 获取历史数据失败: %s", e)
        return f"获取历史数据失败: {e}（数据库无数据，AKShare调用出错）"


def _fetch_stock_financial(stock_code: str) -> str:
    """获取股票财务指标数据（数据库优先 + AKShare 降级）"""
    t0 = time.time()

    # === 1. 优先从数据库查询 ===
    db_data = _query_db_financial(stock_code)
    if db_data:
        logger.info("[耗时] _fetch_stock_financial(DB命中): %.3fs, code=%s", time.time() - t0, stock_code)
        logger.info("[fetch_stock_financial] 数据库命中: code=%s, 共 %d 条, source=%s",
                     stock_code, len(db_data), db_data[0].get("data_source"))
        return json.dumps(db_data, ensure_ascii=False, indent=2)

    logger.info("[fetch_stock_financial] 数据库无数据，尝试 AKShare: code=%s", stock_code)

    # === 2. AKShare 查询 ===
    try:
        import akshare as ak

        # 获取个股财务指标
        df = ak.stock_financial_abstract_ths(symbol=stock_code, indicator="按报告期")
        if df.empty:
            return f"未找到股票代码 {stock_code} 的财务数据（数据库和AKShare均无数据）"

        df = df.head(4)  # 最近4个报告期
        records = df.to_dict(orient="records")
        for record in records:
            for key in record:
                record[key] = str(record[key])

        logger.info("[耗时] _fetch_stock_financial(AKShare): %.3fs, code=%s", time.time() - t0, stock_code)
        return json.dumps(records, ensure_ascii=False, indent=2)
    except ImportError:
        return "AKShare 未安装，无法获取财务数据（数据库也无数据）"
    except Exception as e:
        logger.error("[fetch_stock_financial] 获取财务数据失败: %s", e)
        return f"获取财务数据失败: {e}（数据库无数据，AKShare调用出错）"


def _fetch_stock_news(stock_code: str) -> str:
    """获取个股最新新闻/公告数据"""
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
        logger.error("[fetch_stock_news] 获取新闻数据失败: %s", e)
        return f"获取新闻数据失败: {e}"


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
