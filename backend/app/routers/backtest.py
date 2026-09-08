"""缠论信号历史回测路由（模块三 US3，T043）。

端点（鉴权 ``Depends(get_current_user)``，全部响应附免责声明 FR-016）：
- ``POST /api/v1/backtest/run``        SSE 回测进度流（后台解耦 + Queue，范式 A）
- ``GET  /api/v1/backtest/reports``     报告列表
- ``GET  /api/v1/backtest/reports/{id}``         报告详情（汇总表）
- ``GET  /api/v1/backtest/reports/{id}/details`` 报告明细下钻

回测与监控复用同一 ``ChanlunService``（SC-005 一致性）。比例 Decimal → float 在本路由
序列化层完成（T060）。
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.dtos.backtest_dto import (
    BacktestDetailsResponse,
    BacktestReportDetailResponse,
    BacktestReportListItem,
    BacktestReportMeta,
    BacktestReportsResponse,
    BacktestRunRequest,
    BacktestSignalDetailItem,
    BacktestSummaryCell,
)
from app.application.use_cases.chanlun_backtest import ChanlunBacktestUseCase
from app.application.use_cases.chanlun_calc import ChanlunCalcUseCase
from app.core.database import async_session, get_db
from app.core.deps import CurrentUser, get_current_user
from app.domain.entities.backtest import BacktestSignalDetail, BacktestSummary
from app.domain.services.chanlun_service import normalize_algo_version
from app.infrastructure.repositories.mysql_backtest_repo import MySQLBacktestRepository
from app.infrastructure.repositories.mysql_chanlun_repo import MySQLChanlunRepository
from app.infrastructure.repositories.mysql_stock_data_repo import MySQLStockDataRepository
from app.infrastructure.repositories.mysql_watchlist_repo import MySQLWatchlistRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/backtest", tags=["backtest"])

# 后台 SSE 任务引用集合，避免被 GC 回收
_bg_tasks: set = set()


def _jsonable(obj):
    """递归把 Decimal → float、date/datetime → ISO 字符串。"""
    from datetime import date, datetime
    from decimal import Decimal

    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    return obj


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(_jsonable(data), ensure_ascii=False)}\n\n"


def _build_backtest(
    session: AsyncSession, algo_version: Optional[str] = None
) -> ChanlunBacktestUseCase:
    """从单个 DB session 装配回测 UseCase（复用监控的 calc 依赖）。

    ``algo_version``：双版本并存（2026-09-08），v1/v2 口径回测对照；None 用
    settings 默认版。
    """
    backtest_repo = MySQLBacktestRepository(session)
    calc = ChanlunCalcUseCase(
        stock_data_repo=MySQLStockDataRepository(session),
        chanlun_repo=MySQLChanlunRepository(session),
        algo_version=algo_version,
    )
    return ChanlunBacktestUseCase(
        chanlun_calc=calc, backtest_repo=backtest_repo, algo_version=algo_version
    )


# ---------------------------------------------------------------------------
# POST /run  （SSE，后台解耦 + Queue，范式 A）
# ---------------------------------------------------------------------------

@router.post("/run")
async def run_backtest(
    body: BacktestRunRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """发起回测并流式推送进度；完成后 ``backtest_completed`` 携带 ``report_id``。

    客户端断开后后台任务继续跑完（报告落库不丢）。
    """
    queue: asyncio.Queue = asyncio.Queue()
    state = {"connected": True}

    async def progress_cb(msg: dict) -> None:
        if state["connected"]:
            await queue.put({"event": "backtest_progress", "data": msg})

    async def background() -> None:
        try:
            async with async_session() as session:
                wl_repo = MySQLWatchlistRepository(session)
                if body.stock_codes is not None:
                    codes = sorted(set(body.stock_codes))
                else:
                    items = await wl_repo.get_all_items_by_user(current_user.user_id)
                    codes = sorted({it.stock_code for it in items if it.stock_code})
                if not codes:
                    await queue.put({"event": "backtest_error", "data": {"message": "未找到自选股，无法回测"}})
                    return
                await queue.put({"event": "backtest_started", "data": {"range": body.range, "stock_count": len(codes)}})
                algo_version = normalize_algo_version(body.version) if body.version else None
                bt = _build_backtest(session, algo_version=algo_version)
                report = await bt.run(
                    user_id=current_user.user_id,
                    range_label=body.range,
                    periods=body.periods,
                    stock_codes=codes,
                    progress_cb=progress_cb,
                )
                await session.commit()
                await queue.put({
                    "event": "backtest_completed",
                    "data": {
                        "report_id": report.report_id,
                        "signal_total": report.signal_total,
                        "excluded_invalidated": report.excluded_invalidated,
                        "duration_ms": None,
                    },
                })
        except Exception as e:  # 后台异常不冒泡到已返回的响应
            logger.exception("backtest 后台任务失败")
            await queue.put({"event": "backtest_error", "data": {"message": str(e)}})
        finally:
            await queue.put(None)  # sentinel

    task = asyncio.create_task(background())
    _bg_tasks.add(task)
    task.add_done_callback(_bg_tasks.discard)

    async def event_gen() -> AsyncGenerator[str, None]:
        try:
            while True:
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=30.0)
                except asyncio.TimeoutError:
                    yield _sse("heartbeat", {})
                    continue
                if msg is None:
                    break
                yield _sse(msg["event"], msg["data"])
        except asyncio.CancelledError:
            state["connected"] = False
            logger.info("backtest SSE 客户端断开，后台任务继续")
            raise
        finally:
            state["connected"] = False

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


# ---------------------------------------------------------------------------
# GET /reports
# ---------------------------------------------------------------------------

@router.get("/reports")
async def list_reports(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """报告列表（按 create_time 倒序）。"""
    repo = MySQLBacktestRepository(db)
    reports = await repo.list_reports(current_user.user_id, limit=page_size)
    items = [
        BacktestReportListItem(
            report_id=r.report_id, range_label=r.range_label,
            start_date=r.start_date, end_date=r.end_date,
            stock_count=r.stock_count, signal_total=r.signal_total,
            excluded_invalidated=r.excluded_invalidated,
            algo_version=r.algo_version, status=r.status, create_time=r.create_time,
        )
        for r in reports
    ]
    response = BacktestReportsResponse(items=items, total=len(items))
    return _jsonable(response.model_dump())


# ---------------------------------------------------------------------------
# GET /reports/{id}
# ---------------------------------------------------------------------------

def _summary_to_cell(s: BacktestSummary) -> BacktestSummaryCell:
    return BacktestSummaryCell(
        period=s.period, signal_type=s.signal_type, window=s.window,
        sample=s.sample_count, win_rate=s.win_rate, avg_return=s.avg_return,
        median_return=s.median_return, profit_loss_ratio=s.profit_loss_ratio, note=s.note,
    )


@router.get("/reports/{report_id}")
async def get_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """报告详情：meta + 汇总表。"""
    repo = MySQLBacktestRepository(db)
    report = await repo.get_report(report_id)
    if report is None or report.user_id != current_user.user_id:
        raise HTTPException(status_code=404, detail="回测报告不存在")
    summaries = await repo.get_summaries(report_id)
    response = BacktestReportDetailResponse(
        meta=BacktestReportMeta(
            range_label=report.range_label, stock_count=report.stock_count,
            signal_total=report.signal_total, excluded_invalidated=report.excluded_invalidated,
            algo_version=report.algo_version, benchmark_return=report.benchmark_return,
            finished_at=report.create_time,
        ),
        summary=[_summary_to_cell(s) for s in summaries],
    )
    return _jsonable(response.model_dump())


# ---------------------------------------------------------------------------
# GET /reports/{id}/details
# ---------------------------------------------------------------------------

def _detail_to_item(d: BacktestSignalDetail) -> BacktestSignalDetailItem:
    return BacktestSignalDetailItem(
        stock_code=d.stock_code, signal_type=d.signal_type, signal_time=d.signal_time,
        trigger_price=d.trigger_price, ret_5=d.ret_5, ret_10=d.ret_10,
        ret_20=d.ret_20, ret_60=d.ret_60, window_complete=d.window_complete,
    )


@router.get("/reports/{report_id}/details")
async def get_report_details(
    report_id: int,
    period: Optional[str] = Query(None, pattern="^(daily|m30)$"),
    signal_type: Optional[str] = Query(None, pattern="^(buy1|buy2|buy3|sell1|sell2|sell3)$"),
    window: Optional[int] = Query(None, ge=5, le=60),
    stock_code: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    # 上限 2000：报告详情页需一次拉全量明细在前端做盈亏/分档统计（T048 页面化）
    page_size: int = Query(20, ge=1, le=2000),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """报告明细下钻（可按 period/signal_type/stock_code 过滤）。

    ``window`` 过滤要求该窗口收益非空（近期信号未来窗越界时该窗口为空，应被剔除）。
    """
    repo = MySQLBacktestRepository(db)
    report = await repo.get_report(report_id)
    if report is None or report.user_id != current_user.user_id:
        raise HTTPException(status_code=404, detail="回测报告不存在")

    details = await repo.get_signal_details(report_id, period=period, signal_type=signal_type)
    items = [_detail_to_item(d) for d in details]
    if stock_code:
        items = [it for it in items if it.stock_code == stock_code]
    if window in (5, 10, 20, 60):
        attr = f"ret_{window}"
        items = [it for it in items if getattr(it, attr) is not None]
    total = len(items)
    start = (page - 1) * page_size
    paged = items[start: start + page_size]
    response = BacktestDetailsResponse(items=paged, total=total)
    return _jsonable(response.model_dump())
