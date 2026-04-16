from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any


@dataclass
class IndustryRef:
    """文章关联的行业引用"""
    industry_code: str
    chain_level: Optional[int] = None


@dataclass
class StockRef:
    """文章关联的股票引用"""
    stock_code: str
    stock_name: str


@dataclass
class Article:
    article_id: str
    title: str
    summary: str
    content: str
    event_type: str  # geopolitical/policy/earnings/supply_chain/other
    raw_input: str
    user_id: str
    chain_table: Optional[List[Dict[str, Any]]] = None
    # 关联数据（非持久化，从关联表查询填充）
    industries: List[IndustryRef] = field(default_factory=list)
    stocks: List[StockRef] = field(default_factory=list)
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None
    deleted: str = "0"
