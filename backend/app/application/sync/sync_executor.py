"""Sync task executor — orchestrates data source sync with SSE progress streaming.

Coordinates:
1. DataSourceClient (fetch raw data)
2. DataCleaner (normalize data)
3. StockDataRepository (persist to MySQL)
4. RedisCache (cache hot data)
5. SyncTaskRepository (track task progress)
6. SSE event generator (stream progress to frontend)
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime
from typing import Optional, AsyncGenerator

from app.domain.models.stock_data import (
    SourceType,
    DataType,
    SyncTask,
    SyncStatus,
)
from app.domain.repositories.sync_task_repo import SyncTaskRepository
from app.domain.repositories.datasource_repo import DataSourceRepository
from app.domain.repositories.stock_data_repo import StockDataRepository
from app.domain.services.data_cleaner import (
    clean_basic_info,
    clean_market_quote,
    clean_daily_quote,
    clean_financial,
)
from app.infrastructure.cache.redis_cache import redis_cache

logger = logging.getLogger(__name__)


# Memory lock registry to prevent concurrent syncs per source+type
_locks: dict[str, asyncio.Lock] = {}


def _get_lock(key: str) -> asyncio.Lock:
    """Get or create an async lock for the given key."""
    if key not in _locks:
        _locks[key] = asyncio.Lock()
    return _locks[key]


def _sse_event(event_type: str, data: dict) -> str:
    """Format a Server-Sent Event message."""
    import json
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


class SyncExecutor:
    """Executes data synchronization tasks and streams progress via SSE."""

    def __init__(
        self,
        task_repo: SyncTaskRepository,
        datasource_repo: DataSourceRepository,
        stock_data_repo: StockDataRepository,
    ):
        self.task_repo = task_repo
        self.datasource_repo = datasource_repo
        self.stock_data_repo = stock_data_repo

    async def execute_sync(
        self,
        source_type: SourceType,
        data_type: DataType,
        symbol: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """Execute a sync task and yield SSE events for real-time progress."""

        lock_key = f"{source_type.value}:{data_type.value}"
        lock = _get_lock(lock_key)

        # Check if already running (in-memory lock)
        if lock.locked():
            yield _sse_event("sync_error", {
                "error": "sync_in_progress",
                "message": f"数据源 {source_type.value} 的 {data_type.value} 同步任务正在执行中",
            })
            return

        # Check in database
        existing = await self.task_repo.get_running_by_source(source_type, data_type)
        if existing:
            yield _sse_event("sync_error", {
                "error": "sync_in_progress",
                "message": f"数据源 {source_type.value} 的 {data_type.value} 同步任务正在执行中",
                "running_task_id": existing.task_id,
            })
            return

        # Check datasource is configured
        if not await self.datasource_repo.is_configured(source_type):
            yield _sse_event("sync_error", {
                "error": "datasource_not_configured",
                "message": f"数据源 {source_type.value} 未配置，请先在数据源配置中添加凭证",
            })
            return

        # Create task record
        task = SyncTask(
            task_id=str(uuid.uuid4()),
            source_type=source_type,
            data_type=data_type,
            status=SyncStatus.PENDING,
        )
        task = await self.task_repo.create(task)

        async with lock:
            try:
                # Update to running
                task.start_time = datetime.now()
                await self.task_repo.update_status(
                    task.task_id, SyncStatus.RUNNING, start_time=task.start_time,
                )

                yield _sse_event("sync_started", {
                    "task_id": task.task_id,
                    "source_type": source_type.value,
                    "data_type": data_type.value,
                })

                # Execute the actual sync
                success, fail, total = 0, 0, 0
                async for event in self._execute_data_sync(
                    source_type, data_type, task,
                    symbol, start_date, end_date,
                ):
                    yield event
                    # Parse event data for final stats
                    for line in event.split("\n"):
                        if line.startswith("data: "):
                            import json as _json
                            try:
                                data = _json.loads(line[6:])
                                if data.get("success") is not None:
                                    success = data["success"]
                                    fail = data.get("failed", 0)
                                    total = data.get("total", 0)
                            except (_json.JSONDecodeError, NameError):
                                pass

                task.end_time = datetime.now()
                duration_ms = int((task.end_time - task.start_time).total_seconds() * 1000)

                await self.task_repo.update_status(
                    task.task_id,
                    SyncStatus.COMPLETED,
                    processed_count=total,
                    success_count=success,
                    fail_count=fail,
                    error_message=None,
                )

                yield _sse_event("sync_completed", {
                    "task_id": task.task_id,
                    "total": total,
                    "processed": total,
                    "success": success,
                    "failed": fail,
                    "duration_ms": duration_ms,
                })

                logger.info(
                    "Sync completed: source=%s type=%s total=%d success=%d failed=%d duration=%dms",
                    source_type.value, data_type.value, total, success, fail, duration_ms,
                )

            except Exception as e:
                logger.exception("Sync failed: source=%s type=%s", source_type.value, data_type.value)

                end_time = datetime.now()
                duration_ms = int((end_time - (task.start_time or end_time)).total_seconds() * 1000)

                await self.task_repo.update_status(
                    task.task_id,
                    SyncStatus.FAILED,
                    error_message=str(e),
                )

                yield _sse_event("sync_failed", {
                    "task_id": task.task_id,
                    "error": str(e),
                    "duration_ms": duration_ms,
                })

    async def _execute_data_sync(
        self,
        source_type: SourceType,
        data_type: DataType,
        task: SyncTask,
        symbol: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """Execute the actual data sync. Yields SSE progress events."""

        if source_type == SourceType.TUSHARE:
            from app.application.sync.tushare_client import TushareClient
            from app.core.config import settings

            config = await self.datasource_repo.get_by_type(SourceType.TUSHARE)
            if not config or not config.api_key:
                raise ValueError(f"Tushare API key not configured")

            # Decrypt the API key
            from app.infrastructure.repositories.mysql_datasource_repo import MySQLDataSourceRepository
            import os
            from cryptography.fernet import Fernet
            key = settings.datasource_encryption_key or os.environ.get("DATASOURCE_ENCRYPTION_KEY", "")
            fernet = Fernet(key.encode()) if key else None

            api_key = config.api_key
            if fernet:
                try:
                    api_key = fernet.decrypt(config.api_key.encode()).decode()
                except Exception:
                    api_key = config.api_key

            client = TushareClient(token=api_key)
        elif source_type == SourceType.AKSHARE:
            from app.application.sync.akshare_client import AKShareClient
            client = AKShareClient()
        elif source_type == SourceType.BAOSTOCK:
            from app.application.sync.baostock_client import BaoStockClient
            client = BaoStockClient()
        else:
            raise ValueError(f"Unknown source type: {source_type}")

        source_str = source_type.value
        success = 0
        fail = 0
        total = 0

        if data_type == DataType.BASIC_INFO:
            raw_list = client.fetch_basic_info()

            # 如果指定了股票代码，只同步该股票
            if symbol:
                raw_list = [r for r in raw_list if r.get("code") == symbol or r.get("symbol") == symbol]

            total = len(raw_list)

            if total == 0:
                raise ValueError(f"未找到股票代码: {symbol}")

            yield_progress = self._make_progress_yielder(task.task_id, source_str, data_type.value, total)

            for i, raw in enumerate(raw_list):
                try:
                    entity = clean_basic_info(raw, source_str)
                    await self.stock_data_repo.upsert_basic(entity)
                    success += 1
                except Exception as e:
                    logger.warning("Failed to clean basic info for %s: %s", raw, e)
                    fail += 1

                if (i + 1) % 10 == 0 or i == total - 1:
                    async for evt in yield_progress(i + 1, success, fail):
                        yield evt

            return

        elif data_type == DataType.MARKET_QUOTE:
            raw_list = client.fetch_quote()

            # 如果指定了股票代码，只同步该股票
            if symbol:
                raw_list = [r for r in raw_list if r.get("代码") == symbol or r.get("code") == symbol]

            total = len(raw_list)

            if total == 0:
                raise ValueError(f"未找到股票实时行情: {symbol}")

            yield_progress = self._make_progress_yielder(task.task_id, source_str, data_type.value, total)

            for i, raw in enumerate(raw_list):
                try:
                    entity = clean_market_quote(raw, source_str)
                    await self.stock_data_repo.upsert_quote(entity)
                    # Cache to Redis
                    if entity.code:
                        await redis_cache.set(
                            f"stock:quote:{entity.code}",
                            {"price": str(entity.price), "change_pct": str(entity.change_pct)},
                            ttl=300,  # 5 minutes
                        )
                    success += 1
                except Exception as e:
                    logger.warning("Failed to clean quote for %s: %s", raw, e)
                    fail += 1

                if (i + 1) % 10 == 0 or i == total - 1:
                    async for evt in yield_progress(i + 1, success, fail):
                        yield evt

        elif data_type == DataType.DAILY_QUOTE:
            if not symbol:
                raise ValueError("daily_quote sync requires a symbol parameter")

            if not start_date or not end_date:
                raise ValueError("daily_quote sync requires start_date and end_date parameters")

            raw_list = client.fetch_daily_quote(
                code=symbol, start_date=start_date, end_date=end_date, period="daily",
            )
            total = len(raw_list)

            yield_progress = self._make_progress_yielder(task.task_id, source_str, data_type.value, total)

            quotes = []
            for i, raw in enumerate(raw_list):
                try:
                    entity = clean_daily_quote(raw, source_str)
                    quotes.append(entity)
                    success += 1
                except Exception as e:
                    logger.warning("Failed to clean daily quote for %s: %s", raw, e)
                    fail += 1

                if (i + 1) % 10 == 0 or i == total - 1:
                    async for evt in yield_progress(i + 1, success, fail):
                        yield evt

            if quotes:
                await self.stock_data_repo.upsert_daily_batch(quotes)

            return

        elif data_type == DataType.FINANCIAL:
            if symbol:
                raw_list = client.fetch_financial(code=symbol)
            else:
                # For full market sync, we'd need to iterate all stocks first
                # For MVP, require symbol
                raise ValueError("financial sync requires a symbol parameter for full sync")

            total = len(raw_list)

            yield_progress = self._make_progress_yielder(task.task_id, source_str, data_type.value, total)

            financials = []
            for i, raw in enumerate(raw_list):
                try:
                    entity = clean_financial(raw, source_str)
                    financials.append(entity)
                    success += 1
                except Exception as e:
                    logger.warning("Failed to clean financial for %s: %s", raw, e)
                    fail += 1

                if (i + 1) % 10 == 0 or i == total - 1:
                    async for evt in yield_progress(i + 1, success, fail):
                        yield evt

            if financials:
                await self.stock_data_repo.upsert_financial_batch(financials)

            return

        return

    def _make_progress_yielder(self, task_id, source, data_type, total):
        """Create a closure that yields progress SSE events."""
        async def yield_progress(processed, success, fail):
            import json
            event = f"event: sync_progress\ndata: {json.dumps({
                'task_id': task_id,
                'source_type': source,
                'data_type': data_type,
                'processed': processed,
                'total': total,
                'success': success,
                'failed': fail,
                'status': 'running',
            }, ensure_ascii=False)}\n\n"
            yield event
        return yield_progress
