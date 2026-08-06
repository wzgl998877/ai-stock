"""MySQL Repository 实现回测（模块三）。

对照 ``data-model.md``：报告、明细、聚合统计的读写。
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.backtest import (
    BacktestReport,
    BacktestSignalDetail,
    BacktestSummary,
)
from app.domain.repositories.backtest_repo import BacktestRepository
from app.infrastructure.db.models import (
    BacktestReportModel,
    BacktestSignalDetailModel,
    BacktestSummaryModel,
)


# ---------------------------------------------------------------------------
# ORM ↔ Entity
# ---------------------------------------------------------------------------

def _report_to_entity(m: BacktestReportModel) -> BacktestReport:
    return BacktestReport(
        report_id=m.id,
        user_id=m.user_id,
        range_label=m.range_label,
        start_date=m.start_date,
        end_date=m.end_date,
        stock_count=m.stock_count or 0,
        signal_total=m.signal_total or 0,
        excluded_invalidated=m.excluded_invalidated or 0,
        benchmark_return=m.benchmark_return,
        algo_version=m.algo_version,
        status=m.status,
        create_time=m.create_time,
    )


def _detail_to_entity(m: BacktestSignalDetailModel) -> BacktestSignalDetail:
    return BacktestSignalDetail(
        id=m.id,
        report_id=m.report_id,
        stock_code=m.stock_code,
        period=m.period,
        signal_type=m.signal_type,
        structure_level=m.structure_level,
        signal_time=m.signal_time,
        trigger_price=m.trigger_price,
        ret_5=m.ret_5,
        ret_10=m.ret_10,
        ret_20=m.ret_20,
        ret_60=m.ret_60,
        window_complete=bool(m.window_complete),
    )


def _summary_to_entity(m: BacktestSummaryModel) -> BacktestSummary:
    return BacktestSummary(
        id=m.id,
        report_id=m.report_id,
        period=m.period,
        signal_type=m.signal_type,
        window=m.window,
        sample_count=m.sample_count,
        win_rate=m.win_rate,
        avg_return=m.avg_return,
        median_return=m.median_return,
        profit_loss_ratio=m.profit_loss_ratio,
        note=m.note,
    )


class MySQLBacktestRepository(BacktestRepository):
    """回测 Repository 的 MySQL 实现。"""

    def __init__(self, session: AsyncSession):
        self.session = session

    # --- 报告 ---

    async def create_report(self, report: BacktestReport) -> BacktestReport:
        model = BacktestReportModel(
            user_id=report.user_id,
            range_label=report.range_label,
            start_date=report.start_date,
            end_date=report.end_date,
            stock_count=report.stock_count,
            algo_version=report.algo_version,
            status=report.status or "running",
        )
        self.session.add(model)
        await self.session.flush()
        return _report_to_entity(model)

    async def finish_report(
        self,
        report_id: int,
        status: str,
        signal_total: int,
        excluded_invalidated: int,
        benchmark_return: Optional[float],
    ) -> None:
        bench = Decimal(str(benchmark_return)) if benchmark_return is not None else None
        stmt = (
            update(BacktestReportModel)
            .where(BacktestReportModel.id == report_id)
            .values(
                status=status,
                signal_total=signal_total,
                excluded_invalidated=excluded_invalidated,
                benchmark_return=bench,
            )
        )
        await self.session.execute(stmt)
        await self.session.flush()

    async def get_report(self, report_id: int) -> Optional[BacktestReport]:
        stmt = select(BacktestReportModel).where(BacktestReportModel.id == report_id)
        result = await self.session.execute(stmt)
        m = result.scalar_one_or_none()
        return _report_to_entity(m) if m else None

    async def list_reports(self, user_id: str, limit: int = 20) -> list[BacktestReport]:
        stmt = (
            select(BacktestReportModel)
            .where(BacktestReportModel.user_id == user_id)
            .order_by(BacktestReportModel.create_time.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return [_report_to_entity(m) for m in result.scalars().all()]

    # --- 明细 ---

    async def add_signal_details(self, details: list[BacktestSignalDetail]) -> None:
        if not details:
            return
        for d in details:
            self.session.add(
                BacktestSignalDetailModel(
                    report_id=d.report_id,
                    stock_code=d.stock_code,
                    period=d.period,
                    signal_type=d.signal_type,
                    structure_level=d.structure_level,
                    signal_time=d.signal_time,
                    trigger_price=d.trigger_price,
                    ret_5=d.ret_5,
                    ret_10=d.ret_10,
                    ret_20=d.ret_20,
                    ret_60=d.ret_60,
                    window_complete=int(bool(d.window_complete)),
                )
            )
        await self.session.flush()

    async def get_signal_details(
        self,
        report_id: int,
        period: Optional[str] = None,
        signal_type: Optional[str] = None,
    ) -> list[BacktestSignalDetail]:
        conditions = [BacktestSignalDetailModel.report_id == report_id]
        if period:
            conditions.append(BacktestSignalDetailModel.period == period)
        if signal_type:
            conditions.append(BacktestSignalDetailModel.signal_type == signal_type)
        stmt = (
            select(BacktestSignalDetailModel)
            .where(*conditions)
            .order_by(BacktestSignalDetailModel.signal_time.asc())
        )
        result = await self.session.execute(stmt)
        return [_detail_to_entity(m) for m in result.scalars().all()]

    # --- 聚合 ---

    async def upsert_summaries(self, summaries: list[BacktestSummary]) -> None:
        if not summaries:
            return
        for s in summaries:
            stmt = select(BacktestSummaryModel).where(
                BacktestSummaryModel.report_id == s.report_id,
                BacktestSummaryModel.period == s.period,
                BacktestSummaryModel.signal_type == s.signal_type,
                BacktestSummaryModel.window == s.window,
            )
            result = await self.session.execute(stmt)
            existing = result.scalar_one_or_none()
            values = dict(
                sample_count=s.sample_count,
                win_rate=s.win_rate,
                avg_return=s.avg_return,
                median_return=s.median_return,
                profit_loss_ratio=s.profit_loss_ratio,
                note=s.note,
            )
            if existing is None:
                self.session.add(BacktestSummaryModel(
                    report_id=s.report_id, period=s.period,
                    signal_type=s.signal_type, window=s.window, **values,
                ))
            else:
                for k, v in values.items():
                    setattr(existing, k, v)
        await self.session.flush()

    async def get_summaries(self, report_id: int) -> list[BacktestSummary]:
        stmt = (
            select(BacktestSummaryModel)
            .where(BacktestSummaryModel.report_id == report_id)
            .order_by(BacktestSummaryModel.period, BacktestSummaryModel.signal_type, BacktestSummaryModel.window)
        )
        result = await self.session.execute(stmt)
        return [_summary_to_entity(m) for m in result.scalars().all()]
