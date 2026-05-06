"""分时数据领域实体（仅Redis缓存，不持久化到MySQL）"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


@dataclass
class MinuteQuote:
    """分时数据"""
    stock_code: str = ""
    time: str = ""           # "09:30"
    price: Decimal = Decimal("0")
    volume: Decimal = Decimal("0")
    avg_price: Optional[Decimal] = None
