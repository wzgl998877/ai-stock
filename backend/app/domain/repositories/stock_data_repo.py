"""Repository interface for stock data (basic info, quotes, K-line, financial)."""

from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import Optional, List
from app.domain.models.stock_data import (
    StockBasicInfo,
    MarketQuote,
    StockDailyQuote,
    StockFinancial,
    StockKline30m,
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

    @abstractmethod
    async def get_latest_daily_date(
        self, code: str, period: str = "daily", source: Optional[str] = None
    ) -> Optional[date]:
        """某股最新日 K 日期（日线增量拉取判断缺口用；无数据返回 None）。

        ``source`` 给定时只看该数据源（增量落库按 source 幂等，
        与 ``upsert_daily_batch`` 的删除范围一致）。
        """
        ...

    # --- 30 分钟 K 线（缠论模块三，独立表 t_stock_kline_30m） ---

    @abstractmethod
    async def upsert_kline_30m_batch(self, quotes: List[StockKline30m]) -> None:
        """批量插入/更新 30 分钟 K 线（先删后插，同一批次同 code）"""
        ...

    @abstractmethod
    async def get_kline_30m(
        self,
        code: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[StockKline30m]:
        """获取 30 分钟 K 线（按 trade_time 升序）"""
        ...

    @abstractmethod
    async def get_latest_kline_30m_time(
        self, code: str, closed_before: Optional[datetime] = None
    ) -> Optional[datetime]:
        """获取某股最新的 30m trade_time（监控数据新鲜度检查用）。

        ``closed_before`` 给定时只统计 ``trade_time <= closed_before`` 的行
        （排除盘中 forming K 线，与缠论计算的剔除口径一致）。
        """
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
