"""自选股相关领域实体"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List


@dataclass
class WatchlistGroup:
    """自选股分组"""
    id: Optional[int] = None
    user_id: str = "default"
    name: str = ""
    display_order: int = 0
    is_default: bool = False
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None
    # 运行时字段，非持久化
    stock_count: int = 0
    stocks: List['WatchlistItem'] = field(default_factory=list)


@dataclass
class WatchlistItem:
    """自选股条目"""
    id: Optional[int] = None
    group_id: int = 0
    stock_code: str = ""
    stock_name: str = ""
    add_time: Optional[datetime] = None
    create_time: Optional[datetime] = None
    # 运行时字段（从行情数据填充）
    price: Optional[float] = None
    change_pct: Optional[float] = None
    industry: Optional[str] = None
    signal: Optional[str] = None
    add_price: Optional[float] = None
