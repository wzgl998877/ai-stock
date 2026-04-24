"""Domain entities for stock data source integration."""

from dataclasses import dataclass, field
from datetime import datetime, date
from decimal import Decimal
from typing import Optional
from enum import Enum


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class SourceType(str, Enum):
    TUSHARE = "tushare"
    AKSHARE = "akshare"
    BAOSTOCK = "baostock"


class DataType(str, Enum):
    BASIC_INFO = "basic_info"
    MARKET_QUOTE = "market_quote"
    DAILY_QUOTE = "daily_quote"
    FINANCIAL = "financial"


class SyncStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# DataSourceConfig
# ---------------------------------------------------------------------------

@dataclass
class DataSourceConfig:
    source_type: SourceType
    api_key: Optional[str] = None  # Encrypted value
    is_enabled: bool = True
    priority: int = 99
    config_json: Optional[dict] = None
    id: Optional[int] = None
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None

    def is_configured(self) -> bool:
        """Whether this datasource has valid credentials."""
        if self.source_type == SourceType.AKSHARE:
            return True  # AKShare doesn't need API key
        if self.source_type == SourceType.BAOSTOCK:
            return self.is_enabled  # BaoStock uses login, not key
        return bool(self.api_key)


# ---------------------------------------------------------------------------
# SyncTask
# ---------------------------------------------------------------------------

@dataclass
class SyncTask:
    task_id: str
    source_type: SourceType
    data_type: DataType
    status: SyncStatus = SyncStatus.PENDING
    total_count: int = 0
    processed_count: int = 0
    success_count: int = 0
    fail_count: int = 0
    error_message: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_ms: Optional[int] = None
    id: Optional[int] = None
    create_time: Optional[datetime] = None

    def to_progress_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "source_type": self.source_type.value,
            "data_type": self.data_type.value,
            "status": self.status.value,
            "total": self.total_count,
            "processed": self.processed_count,
            "success": self.success_count,
            "failed": self.fail_count,
        }


# ---------------------------------------------------------------------------
# Stock Data Entities
# ---------------------------------------------------------------------------

@dataclass
class StockBasicInfo:
    code: str
    name: str
    exchange: Optional[str] = None
    market_type: Optional[str] = None
    industry: Optional[str] = None
    list_date: Optional[date] = None
    is_active: bool = True
    data_source: str = ""
    update_time: Optional[datetime] = None


@dataclass
class MarketQuote:
    code: str
    price: Optional[Decimal] = None
    change_pct: Optional[Decimal] = None
    change_amount: Optional[Decimal] = None
    volume: Optional[Decimal] = None
    amount: Optional[Decimal] = None
    open_price: Optional[Decimal] = None
    high_price: Optional[Decimal] = None
    low_price: Optional[Decimal] = None
    pre_close: Optional[Decimal] = None
    quote_time: Optional[datetime] = None
    data_source: str = ""
    id: Optional[int] = None
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None


@dataclass
class StockDailyQuote:
    code: str
    trade_date: date
    period: str  # daily, weekly, monthly
    open_price: Optional[Decimal] = None
    high_price: Optional[Decimal] = None
    low_price: Optional[Decimal] = None
    close_price: Optional[Decimal] = None
    pre_close: Optional[Decimal] = None
    volume: Optional[Decimal] = None
    amount: Optional[Decimal] = None
    pct_chg: Optional[Decimal] = None
    data_source: str = ""
    id: Optional[int] = None
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None


@dataclass
class StockFinancial:
    code: str
    report_date: date
    roe: Optional[Decimal] = None
    net_profit: Optional[Decimal] = None
    revenue: Optional[Decimal] = None
    eps: Optional[Decimal] = None
    gross_margin: Optional[Decimal] = None
    debt_ratio: Optional[Decimal] = None
    data_source: str = ""
    id: Optional[int] = None
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None
