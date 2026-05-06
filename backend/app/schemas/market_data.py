"""行情数据模块 Pydantic Schemas — 请求/响应模型"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# 分时数据
# ---------------------------------------------------------------------------

class MinuteQuoteResponse(BaseModel):
    """分时数据响应"""
    stock_code: str
    time: str
    price: Decimal
    volume: Decimal
    avg_price: Optional[Decimal] = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# 技术指标
# ---------------------------------------------------------------------------

class StockIndicatorResponse(BaseModel):
    """技术指标响应"""
    stock_code: str
    trade_date: Optional[date] = None
    period: str = "daily"
    ma5: Optional[Decimal] = None
    ma10: Optional[Decimal] = None
    ma20: Optional[Decimal] = None
    macd_dif: Optional[Decimal] = None
    macd_dea: Optional[Decimal] = None
    macd_bar: Optional[Decimal] = None
    kdj_k: Optional[Decimal] = None
    kdj_d: Optional[Decimal] = None
    kdj_j: Optional[Decimal] = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# 股票详情（聚合响应）
# ---------------------------------------------------------------------------

class BasicInfoPart(BaseModel):
    """基础信息部分"""
    stock_code: str
    name: str
    exchange: Optional[str] = None
    industry: Optional[str] = None
    industry_code: Optional[str] = None
    total_market_cap: Optional[Decimal] = None
    float_market_cap: Optional[Decimal] = None
    list_date: Optional[date] = None


class QuotePart(BaseModel):
    """行情部分"""
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


class FinancialPart(BaseModel):
    """财务数据部分"""
    report_date: Optional[date] = None
    roe: Optional[Decimal] = None
    net_profit: Optional[Decimal] = None
    revenue: Optional[Decimal] = None
    eps: Optional[Decimal] = None
    gross_margin: Optional[Decimal] = None
    debt_ratio: Optional[Decimal] = None


class StockDetailResponse(BaseModel):
    """股票详情聚合响应"""
    basic: Optional[BasicInfoPart] = None
    quote: Optional[QuotePart] = None
    financials: List[FinancialPart] = Field(default_factory=list)
    related_articles: List[dict] = Field(default_factory=list)

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# 搜索
# ---------------------------------------------------------------------------

class SearchItem(BaseModel):
    """搜索结果条目"""
    stock_code: str
    name: str
    exchange: Optional[str] = None
    industry: Optional[str] = None


class SearchResponse(BaseModel):
    """搜索响应"""
    items: List[SearchItem] = Field(default_factory=list)
    total: int = 0


# ---------------------------------------------------------------------------
# 自选股
# ---------------------------------------------------------------------------

class WatchlistGroupCreate(BaseModel):
    """创建自选股分组请求"""
    name: str = Field(..., max_length=10, description="分组名称")


class WatchlistGroupUpdate(BaseModel):
    """更新自选股分组请求"""
    name: Optional[str] = Field(None, max_length=10, description="分组名称")
    display_order: Optional[int] = Field(None, description="排序")


class WatchlistGroupResponse(BaseModel):
    """自选股分组响应"""
    id: int
    name: str
    display_order: int = 0
    is_default: bool = False
    stock_count: int = 0
    create_time: Optional[datetime] = None

    model_config = {"from_attributes": True}


class WatchlistItemCreate(BaseModel):
    """添加自选股请求"""
    stock_code: str = Field(..., max_length=10, description="股票代码")
    stock_name: str = Field(..., max_length=50, description="股票名称")


class WatchlistItemResponse(BaseModel):
    """自选股条目响应"""
    id: int
    group_id: int
    stock_code: str
    stock_name: str
    add_time: Optional[datetime] = None
    # 运行时填充
    price: Optional[float] = None
    change_pct: Optional[float] = None
    industry: Optional[str] = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# 行业
# ---------------------------------------------------------------------------

class IndustryStockResponse(BaseModel):
    """行业内股票响应"""
    industry_code: str
    industry_name: str
    stocks: List[SearchItem] = Field(default_factory=list)
    stock_count: int = 0
