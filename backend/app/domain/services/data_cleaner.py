"""Data cleaning and normalization service for stock data.

Handles raw data from different sources (Tushare, AKShare, BaoStock)
and converts them to standardized domain entities.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Any

from app.domain.models.stock_data import (
    StockBasicInfo,
    MarketQuote,
    StockDailyQuote,
    StockFinancial,
)


def _to_decimal(value: Any) -> Decimal | None:
    """Safely convert to Decimal, return None on failure.

    支持带单位的字符串，如 '17.89%'、'454.03亿'、'910.94万'。
    """
    if value is None or value == "":
        return None
    try:
        s = str(value).strip().replace(",", "")
        # 处理百分比: '17.89%' -> 17.89
        if s.endswith("%"):
            s = s[:-1]
        # 处理中文单位: 亿、万
        multiplier = Decimal("1")
        if s.endswith("亿"):
            s = s[:-1]
            multiplier = Decimal("100000000")
        elif s.endswith("万"):
            s = s[:-1]
            multiplier = Decimal("10000")
        return Decimal(s) * multiplier
    except Exception:
        return None


def _format_date(value: Any) -> date | None:
    """Parse date string in various formats to date object."""
    if value is None or value == "":
        return None
    for fmt in ("%Y-%m-%d", "%Y%m%d", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(str(value), fmt).date()
        except (ValueError, TypeError):
            continue
    return None


def _parse_datetime(value: Any) -> datetime | None:
    """Parse datetime string."""
    if value is None or value == "":
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y%m%d%H%M%S"):
        try:
            return datetime.strptime(str(value), fmt)
        except (ValueError, TypeError):
            continue
    return None


def normalize_code(code: str) -> str:
    """Normalize stock code to 6-digit format."""
    return str(code).strip().zfill(6)


# ---------------------------------------------------------------------------
# Cleaners
# ---------------------------------------------------------------------------

def clean_basic_info(raw: dict, source: str) -> StockBasicInfo:
    """Clean raw stock basic info from any source into standardized entity.

    Tushare format: ts_code, name, industry, list_date, exchange
    AKShare format: 代码, 名称, 行业, 上市日期
    BaoStock format: code, code_name, industry, ipoDate, market
    """
    code = normalize_code(
        raw.get("code")
        or raw.get("ts_code", "").split(".")[0]
        or raw.get("symbol", "")
        or ""
    )

    name = (
        raw.get("name")
        or raw.get("名称")
        or raw.get("code_name")
        or ""
    )

    industry = (
        raw.get("industry")
        or raw.get("行业")
        or raw.get("industry_name")
    )

    list_date = _format_date(
        raw.get("list_date")
        or raw.get("上市日期")
        or raw.get("ipoDate")
    )

    market_type = raw.get("market_type") or raw.get("market")

    exchange = raw.get("exchange") or raw.get("交易所")

    return StockBasicInfo(
        code=code,
        name=name,
        exchange=exchange,
        market_type=market_type,
        industry=industry,
        list_date=list_date,
        is_active=True,
        data_source=source,
        update_time=datetime.now(),
    )


def clean_market_quote(raw: dict, source: str) -> MarketQuote:
    """Clean raw market quote into standardized entity.

    Tushare: price, pct_chg, amount (千元), vol (手), trade_date
    AKShare: 最新价, 涨跌幅, 涨跌额, 成交量, 成交额
    """
    price = _to_decimal(
        raw.get("price") or raw.get("最新价") or raw.get("close")
    )
    change_pct = _to_decimal(
        raw.get("pct_chg") or raw.get("涨跌幅")
    )
    change_amount = _to_decimal(
        raw.get("change") or raw.get("涨跌额")
    )
    pre_close = _to_decimal(
        raw.get("pre_close") or raw.get("昨收")
    )

    # Volume: Tushare uses hands (手 = 100 shares), AKShare uses shares directly
    vol_raw = raw.get("volume") or raw.get("vol") or raw.get("成交量")
    volume = _to_decimal(vol_raw)
    if volume and source == "tushare":
        volume = volume * 100  # Convert hands to shares

    # Amount: Tushare uses 千元, AKShare uses 元
    amount_raw = raw.get("amount") or raw.get("成交额")
    amount = _to_decimal(amount_raw)
    if amount and source == "tushare":
        amount = amount * 1000  # Convert 千元 to 元

    quote_time = _parse_datetime(
        raw.get("quote_time")
        or raw.get("trade_time")
        or raw.get("trade_date")
    ) or datetime.now()

    open_price = _to_decimal(raw.get("open") or raw.get("今开"))
    high_price = _to_decimal(raw.get("high") or raw.get("最高"))
    low_price = _to_decimal(raw.get("low") or raw.get("最低"))

    code = normalize_code(
        raw.get("code") or raw.get("ts_code", "").split(".")[0] or ""
    )

    return MarketQuote(
        code=code,
        price=price,
        change_pct=change_pct,
        change_amount=change_amount,
        volume=volume,
        amount=amount,
        open_price=open_price,
        high_price=high_price,
        low_price=low_price,
        pre_close=pre_close,
        quote_time=quote_time,
        data_source=source,
    )


def clean_daily_quote(raw: dict, source: str) -> StockDailyQuote:
    """Clean raw daily K-line data into standardized entity."""
    code = normalize_code(
        raw.get("code") or raw.get("ts_code", "").split(".")[0] or ""
    )

    trade_date = _format_date(
        raw.get("trade_date") or raw.get("date") or raw.get("日期")
    ) or date.today()

    period = raw.get("period") or "daily"

    open_price = _to_decimal(raw.get("open") or raw.get("开盘"))
    high_price = _to_decimal(raw.get("high") or raw.get("最高"))
    low_price = _to_decimal(raw.get("low") or raw.get("最低"))
    close_price = _to_decimal(raw.get("close") or raw.get("收盘"))
    pre_close = _to_decimal(raw.get("pre_close") or raw.get("前收盘"))

    vol_raw = raw.get("volume") or raw.get("vol") or raw.get("成交量")
    volume = _to_decimal(vol_raw)
    if volume and source == "tushare":
        volume = volume * 100

    amount_raw = raw.get("amount") or raw.get("成交额")
    amount = _to_decimal(amount_raw)
    if amount and source == "tushare":
        amount = amount * 1000

    pct_chg = _to_decimal(
        raw.get("pct_chg") or raw.get("涨跌幅") or raw.get("change_pct")
    )

    return StockDailyQuote(
        code=code,
        trade_date=trade_date,
        period=period,
        open_price=open_price,
        high_price=high_price,
        low_price=low_price,
        close_price=close_price,
        pre_close=pre_close,
        volume=volume,
        amount=amount,
        pct_chg=pct_chg,
        data_source=source,
    )


def clean_financial(raw: dict, source: str) -> StockFinancial:
    """Clean raw financial data into standardized entity."""
    code = normalize_code(
        raw.get("code") or raw.get("ts_code", "").split(".")[0] or ""
    )

    report_date = _format_date(
        raw.get("report_date")
        or raw.get("end_date")
        or raw.get("报告期")
    )

    roe = _to_decimal(raw.get("roe") or raw.get("净资产收益率") or raw.get("roe_dt"))
    net_profit = _to_decimal(raw.get("net_profit") or raw.get("净利润"))
    revenue = _to_decimal(raw.get("revenue") or raw.get("营业总收入") or raw.get("营业收入"))
    eps = _to_decimal(raw.get("eps") or raw.get("基本每股收益"))
    gross_margin = _to_decimal(raw.get("gross_margin") or raw.get("销售毛利率") or raw.get("毛利率"))
    debt_ratio = _to_decimal(raw.get("debt_ratio") or raw.get("资产负债率"))

    return StockFinancial(
        code=code,
        report_date=report_date or date.today(),
        roe=roe,
        net_profit=net_profit,
        revenue=revenue,
        eps=eps,
        gross_margin=gross_margin,
        debt_ratio=debt_ratio,
        data_source=source,
    )
