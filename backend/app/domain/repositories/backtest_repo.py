"""回测 Repository 接口（模块三），对标 ``t_backtest_report`` / ``t_backtest_signal_detail`` / ``t_backtest_summary``。"""

from abc import ABC, abstractmethod
from typing import Optional

from app.domain.entities.backtest import (
    BacktestReport,
    BacktestSignalDetail,
    BacktestSummary,
)


class BacktestRepository(ABC):
    """缠论信号回测数据访问接口。"""

    # --- 报告 ---

    @abstractmethod
    async def create_report(self, report: BacktestReport) -> BacktestReport:
        """创建回测报告（status=running），返回带 ``report_id`` 的报告。"""
        ...

    @abstractmethod
    async def finish_report(
        self,
        report_id: int,
        status: str,
        signal_total: int,
        excluded_invalidated: int,
        benchmark_return: Optional[float],
    ) -> None:
        """结束报告（写终态计数 + 基准涨跌）。"""
        ...

    @abstractmethod
    async def get_report(self, report_id: int) -> Optional[BacktestReport]:
        """按 id 取报告。"""
        ...

    @abstractmethod
    async def list_reports(self, user_id: str, limit: int = 20) -> list[BacktestReport]:
        """列出用户最近的回测报告（按 create_time 倒序）。"""
        ...

    # --- 明细 ---

    @abstractmethod
    async def add_signal_details(self, details: list[BacktestSignalDetail]) -> None:
        """批量写入信号明细。"""
        ...

    @abstractmethod
    async def get_signal_details(
        self,
        report_id: int,
        period: Optional[str] = None,
        signal_type: Optional[str] = None,
    ) -> list[BacktestSignalDetail]:
        """查询报告明细（可按 period/signal_type 过滤）。"""
        ...

    # --- 聚合 ---

    @abstractmethod
    async def upsert_summaries(self, summaries: list[BacktestSummary]) -> None:
        """批量覆盖写入聚合统计（同报告同窗口唯一）。"""
        ...

    @abstractmethod
    async def get_summaries(self, report_id: int) -> list[BacktestSummary]:
        """取报告的全部聚合行。"""
        ...
