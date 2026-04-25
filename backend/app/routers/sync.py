"""Sync API router — endpoints for data synchronization.

Provides:
- GET /api/v1/sync/execute — SSE endpoint for triggering sync with progress streaming
- GET /api/v1/sync/tasks — Paginated sync history
- POST /api/v1/sync/tasks/{task_id}/retry — Retry a failed task
"""

import asyncio
import json
import logging
from typing import Optional
from fastapi import APIRouter, Query, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.domain.models.stock_data import SourceType, DataType
from app.domain.repositories.sync_task_repo import SyncTaskRepository
from app.domain.repositories.datasource_repo import DataSourceRepository
from app.domain.repositories.stock_data_repo import StockDataRepository
from app.infrastructure.repositories.mysql_sync_task_repo import MySQLSyncTaskRepository
from app.infrastructure.repositories.mysql_datasource_repo import MySQLDataSourceRepository
from app.infrastructure.repositories.mysql_stock_data_repo import MySQLStockDataRepository
from app.application.sync.sync_executor import SyncExecutor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/sync", tags=["sync"])


@router.get("/execute")
async def execute_sync(
    source_type: str = Query(..., description="数据源类型: tushare/akshare/baostock"),
    data_type: str = Query(..., description="数据类型: basic_info/market_quote/daily_quote/financial"),
    symbol: Optional[str] = Query(None, description="指定股票代码（单股同步）"),
    start_date: Optional[str] = Query(None, description="起始日期（仅daily_quote）"),
    end_date: Optional[str] = Query(None, description="结束日期（仅daily_quote）"),
    db: AsyncSession = Depends(get_db),
):
    """Trigger data sync and stream progress via SSE."""
    try:
        src = SourceType(source_type)
    except ValueError:
        err_body = {"error": "invalid_source_type", "message": f"无效的数据源类型: {source_type}"}
        logger.warning("[GET] /api/v1/sync/execute | 返回=%s", json.dumps(err_body, ensure_ascii=False))
        return err_body

    try:
        dt = DataType(data_type)
    except ValueError:
        err_body = {"error": "invalid_data_type", "message": f"无效的数据类型: {data_type}"}
        logger.warning("[GET] /api/v1/sync/execute | 返回=%s", json.dumps(err_body, ensure_ascii=False))
        return err_body

    task_repo = MySQLSyncTaskRepository(db)
    datasource_repo = MySQLDataSourceRepository(db)
    stock_data_repo = MySQLStockDataRepository(db)
    executor = SyncExecutor(task_repo, datasource_repo, stock_data_repo)

    async def event_generator():
        try:
            async for event in executor.execute_sync(
                source_type=src,
                data_type=dt,
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
            ):
                # 记录每个 SSE 事件到日志
                for line in event.split("\n"):
                    if line.startswith("data: "):
                        data_str = line[6:].strip()
                        if data_str:
                            logger.info("[SSE响应] %s | data=%s", data_type, data_str)
                        break
                yield event
        except asyncio.CancelledError:
            # SSE client disconnected — sync continues in background
            logger.info("SSE client disconnected, sync continues in background (source=%s type=%s)", src.value, dt.value)
        except Exception:
            # No need to rollback here — data writes are managed by the
            # background coroutine with its own session
            raise

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/tasks")
async def list_sync_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    source_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List sync task history with pagination and filters."""
    repo = MySQLSyncTaskRepository(db)

    src = None
    if source_type:
        try:
            src = SourceType(source_type)
        except ValueError:
            pass

    st = None
    if status:
        from app.domain.models.stock_data import SyncStatus
        try:
            st = SyncStatus(status)
        except ValueError:
            pass

    items, total = await repo.list_tasks(page, page_size, source_type=src, status=st)

    return {
        "data": {
            "items": [
                {
                    "task_id": t.task_id,
                    "source_type": t.source_type.value,
                    "data_type": t.data_type.value,
                    "status": t.status.value,
                    "total_count": t.total_count,
                    "processed_count": t.processed_count,
                    "success_count": t.success_count,
                    "fail_count": t.fail_count,
                    "error_message": t.error_message,
                    "start_time": t.start_time.isoformat() if t.start_time else None,
                    "end_time": t.end_time.isoformat() if t.end_time else None,
                    "duration_ms": t.duration_ms,
                }
                for t in items
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    }


@router.post("/tasks/{task_id}/retry")
async def retry_sync_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Retry a failed sync task."""
    repo = MySQLSyncTaskRepository(db)

    task = await repo.get_by_id(task_id)
    if not task:
        return {"error": "task_not_found", "message": f"任务 {task_id} 不存在"}

    if task.status.value == "running":
        return {"error": "sync_in_progress", "message": "该任务正在执行中"}

    datasource_repo = MySQLDataSourceRepository(db)
    stock_data_repo = MySQLStockDataRepository(db)
    executor = SyncExecutor(repo, datasource_repo, stock_data_repo)

    async def event_generator():
        try:
            async for event in executor.execute_sync(
                source_type=task.source_type,
                data_type=task.data_type,
            ):
                yield event
        except asyncio.CancelledError:
            logger.info("SSE client disconnected during retry, sync continues in background")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
