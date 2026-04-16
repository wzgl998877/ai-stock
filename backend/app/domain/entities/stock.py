from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class Stock:
    stock_code: str
    name: str
    exchange: str  # SH/SZ/BJ
    full_name: Optional[str] = None
    list_date: Optional[date] = None
    is_active: bool = True
