"""Repository interface for stock data (basic info, quotes, K-line, financial)."""

from abc import ABC, abstractmethod
from typing import Optional, List
from app.domain.models.stock_data import (
    StockBasicInfo,
    MarketQuote,
    StockDailyQuote,
    StockFinancial,
)


class StockDataRepository(ABC):
    # --- Basic Info ---

    @abstractmethod
    async def upsert_basic(self, info: StockBasicInfo) -> None:
        """插入或更新股票基础信息（按 code + data_source 唯一）"""
        ...

    @abstractmethod
    async def get_basic(self, code: str) -> Optional[StockBasicInfo]:
        """获取股票基础信息（返回优先级最高的数据源）"""
        ...

    @abstractmethod
    async def get_basic_all_sources(self, code: str) -> List[StockBasicInfo]:
        """获取某股票所有数据源的基础信息"""
        ...

    @abstractmethod
    async def get_all_stocks(self) -> List[StockBasicInfo]:
        """获取所有股票基础信息（用于股票列表查询/验证）"""
        ...

    # --- Market Quote ---

    @abstractmethod
    async def upsert_quote(self, quote: MarketQuote) -> None:
        """插入或更新实时行情"""
        ...

    @abstractmethod
    async def get_quote(self, code: str) -> Optional[MarketQuote]:
        """获取最新行情（返回优先级最高的数据源）"""
        ...

    @abstractmethod
    async def get_quotes_batch(self, codes: List[str]) -> List[MarketQuote]:
        """批量获取多只股票最新行情"""
        ...

    # --- Daily Quote (K-line) ---

    @abstractmethod
    async def upsert_daily(self, quote: StockDailyQuote) -> None:
        """插入或更新日K线数据"""
        ...

    @abstractmethod
    async def upsert_daily_batch(self, quotes: List[StockDailyQuote]) -> None:
        """批量插入或更新日K线数据"""
        ...

    @abstractmethod
    async def get_daily(
        self,
        code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: str = "daily",
    ) -> List[StockDailyQuote]:
        """获取历史K线（返回优先级最高的数据源）"""
        ...

    # --- Financial Data ---

    @abstractmethod
    async def upsert_financial(self, data: StockFinancial) -> None:
        """插入或更新财务数据"""
        ...

    @abstractmethod
    async def upsert_financial_batch(self, data_list: List[StockFinancial]) -> None:
        """批量插入或更新财务数据"""
        ...

    @abstractmethod
    async def get_financial(self, code: str) -> List[StockFinancial]:
        """获取财务数据（返回优先级最高的数据源）"""
        ...
