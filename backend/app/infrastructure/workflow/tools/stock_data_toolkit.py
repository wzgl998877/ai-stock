"""金融数据工具集 — 基于 AKShare 的A股数据获取工具（含 BaoStock 降级 + 超时重试 + 缓存）"""

import json
import logging
import time
from typing import Any

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# 超时重试配置
MAX_RETRIES = 2
RETRY_DELAY = 1  # 秒

# === 行情缓存（避免每次拉全市场数据） ===
_spot_cache: dict | None = None
_spot_cache_time: float = 0
_SPOT_CACHE_TTL = 300  # 5分钟缓存


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
    """获取股票实时/最新行情数据"""
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
                return json.dumps(result, ensure_ascii=False, indent=2)
        except Exception as cache_err:
            logger.warning("[fetch_stock_quote] 缓存读取失败，降级到直接查询: %s", cache_err)
            # 清除坏缓存
            global _spot_cache
            _spot_cache = None
    except ImportError:
        return "AKShare 未安装，无法获取行情数据"
    except Exception as e:
        logger.error("[fetch_stock_quote] AKShare获取行情数据失败: %s，尝试BaoStock降级", e)
        # BaoStock 降级
        try:
            import baostock as bs
            lg = bs.login()
            if lg.error_code != '0':
                return f"获取行情数据失败(AKShare: {e}; BaoStock登录失败)"

            # BaoStock 需要带市场前缀
            prefix = "sh" if stock_code.startswith(("6", "9")) else "sz"
            rs = bs.query_history_k_data_plus(
                f"{prefix}.{stock_code}",
                "date,code,open,high,low,close,volume,amount,turn,pctChg",
                start_date="", end_date="",
                frequency="d", adjustflag="2"
            )

            if rs.error_code != '0':
                bs.logout()
                return f"获取行情数据失败(AKShare: {e}; BaoStock查询失败: {rs.error_msg})"

            rows = []
            while (rs.error_code == '0') and rs.next():
                rows.append(rs.get_row_data())

            bs.logout()

            if not rows:
                return f"未找到股票代码 {stock_code} 的行情数据(AKShare: {e}; BaoStock无数据)"

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
            return f"获取行情数据失败: AKShare报错({e})，BaoStock未安装"
        except Exception as e2:
            return f"获取行情数据失败: AKShare({e})，BaoStock({e2})"


def _fetch_stock_history(stock_code: str, period: str = "daily", days: int = 60) -> str:
    """获取股票历史K线数据"""
    try:
        import akshare as ak

        df = ak.stock_zh_a_hist(symbol=stock_code, period=period, adjust="qfq")
        if df.empty:
            return f"未找到股票代码 {stock_code} 的历史数据"

        # 只取最近 days 天
        df = df.tail(days)
        records = df.to_dict(orient="records")
        # 转换值为字符串以确保 JSON 可序列化
        for record in records:
            for key in record:
                record[key] = str(record[key])

        return json.dumps(records, ensure_ascii=False, indent=2)
    except ImportError:
        return "AKShare 未安装，无法获取历史数据"
    except Exception as e:
        logger.error("[fetch_stock_history] 获取历史数据失败: %s", e)
        return f"获取历史数据失败: {e}"


def _fetch_stock_financial(stock_code: str) -> str:
    """获取股票财务指标数据（基本面）"""
    try:
        import akshare as ak

        # 获取个股财务指标
        df = ak.stock_financial_abstract_ths(symbol=stock_code, indicator="按报告期")
        if df.empty:
            return f"未找到股票代码 {stock_code} 的财务数据"

        df = df.head(4)  # 最近4个报告期
        records = df.to_dict(orient="records")
        for record in records:
            for key in record:
                record[key] = str(record[key])

        return json.dumps(records, ensure_ascii=False, indent=2)
    except ImportError:
        return "AKShare 未安装，无法获取财务数据"
    except Exception as e:
        logger.error("[fetch_stock_financial] 获取财务数据失败: %s", e)
        return f"获取财务数据失败: {e}"


def _fetch_stock_news(stock_code: str) -> str:
    """获取个股最新新闻/公告数据"""
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
