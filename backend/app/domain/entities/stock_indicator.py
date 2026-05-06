"""技术指标领域实体"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Optional


@dataclass
class StockIndicator:
    """技术指标计算结果缓存"""
    id: Optional[int] = None
    stock_code: str = ""
    trade_date: Optional[date] = None
    period: str = "daily"

    # MA
    ma5: Optional[Decimal] = None
    ma10: Optional[Decimal] = None
    ma20: Optional[Decimal] = None

    # MACD
    macd_dif: Optional[Decimal] = None
    macd_dea: Optional[Decimal] = None
    macd_bar: Optional[Decimal] = None

    # KDJ
    kdj_k: Optional[Decimal] = None
    kdj_d: Optional[Decimal] = None
    kdj_j: Optional[Decimal] = None

    data_source: str = ""
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None
