from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any


@dataclass
class IndustryRef:
    """文章关联的行业引用"""
    industry_code: str
    chain_level: Optional[int] = None
    sentiment: Optional[str] = None


@dataclass
class StockRef:
    """文章关联的股票引用"""
    stock_code: str
    stock_name: str
    sentiment: Optional[str] = None


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
    article_type: str = "event"
    analysis_data: Optional[Dict[str, Any]] = None
    status: str = "completed"  # in_progress / completed / stopped
    # 关联数据（非持久化，从关联表查询填充）
    industries: List[IndustryRef] = field(default_factory=list)
    stocks: List[StockRef] = field(default_factory=list)
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None
    deleted: str = "0"
