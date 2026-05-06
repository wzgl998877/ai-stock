"""行情数据模块 DTO — 应用层数据传输对象"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List


@dataclass
class StockDetailDTO:
    """股票详情聚合 DTO"""
    stock_code: str = ""
    name: str = ""
    exchange: Optional[str] = None
    industry: Optional[str] = None
    industry_code: Optional[str] = None
    total_market_cap: Optional[Decimal] = None
    float_market_cap: Optional[Decimal] = None
    list_date: Optional[date] = None

    # 行情
    price: Optional[Decimal] = None
    change_pct: Optional[Decimal] = None
    change_amount: Optional[Decimal] = None
    open_price: Optional[Decimal] = None
    high_price: Optional[Decimal] = None
    low_price: Optional[Decimal] = None
    pre_close: Optional[Decimal] = None
    volume: Optional[Decimal] = None
    amount: Optional[Decimal] = None
    pe_ttm: Optional[Decimal] = None
    pb: Optional[Decimal] = None
    quote_time: Optional[datetime] = None

    # 财务（最近一期）
    report_date: Optional[date] = None
    roe: Optional[Decimal] = None
    net_profit: Optional[Decimal] = None
    revenue: Optional[Decimal] = None
    eps: Optional[Decimal] = None
    gross_margin: Optional[Decimal] = None
    debt_ratio: Optional[Decimal] = None

    # 关联文章
    related_articles: List[dict] = field(default_factory=list)


@dataclass
class SearchDTO:
    """搜索 DTO"""
    keyword: str = ""
    stock_code: Optional[str] = None
    stock_name: Optional[str] = None
    exchange: Optional[str] = None
    industry: Optional[str] = None
    page: int = 1
    page_size: int = 20


@dataclass
class SearchResultItem:
    """搜索结果条目"""
    stock_code: str = ""
    name: str = ""
    exchange: Optional[str] = None
    industry: Optional[str] = None


@dataclass
class IndustryOverviewDTO:
    """行业概览 DTO"""
    industry_code: str = ""
    industry_name: str = ""
    stock_count: int = 0
    top_stocks: List[SearchResultItem] = field(default_factory=list)
