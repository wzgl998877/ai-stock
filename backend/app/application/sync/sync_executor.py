"""Sync task executor — orchestrates data source sync with SSE progress streaming.

Coordinates:
1. DataSourceClient (fetch raw data)
2. DataCleaner (normalize data)
3. StockDataRepository (persist to MySQL)
4. RedisCache (cache hot data)
5. SyncTaskRepository (track task progress)
6. SSE event generator (stream progress to frontend)

Design: SSE generator (execute_sync) is decoupled from the actual sync
execution (_run_sync_background). The background coroutine runs with its
own DB session so that SSE client disconnection does NOT interrupt the
sync. Progress events flow through an asyncio.Queue.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Optional, AsyncGenerator

from sqlalchemy.exc import IntegrityError

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

# Background task references (prevent GC)
_background_tasks: set[asyncio.Task] = set()


def _get_lock(key: str) -> asyncio.Lock:
    """Get or create an async lock for the given key."""
    if key not in _locks:
        _locks[key] = asyncio.Lock()
    return _locks[key]


def _sse_event(event_type: str, data: dict) -> str:
    """Format a Server-Sent Event message."""
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
        """Execute a sync task — SSE frontend that consumes progress from background coroutine.

        The actual sync runs in a background asyncio.Task with its own DB session.
        This generator only reads progress events from an asyncio.Queue and yields
        them as SSE messages. If the SSE client disconnects, the background task
        continues to completion.
        """

        lock_key = f"{source_type.value}:{data_type.value}"
        lock = _get_lock(lock_key)

        # Quick check: if lock is held, another sync is running
        if lock.locked():
            yield _sse_event("sync_error", {
                "error": "sync_in_progress",
                "message": f"数据源 {source_type.value} 的 {data_type.value} 同步任务正在执行中",
            })
            return

        # Check in database for running tasks
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

        # Acquire lock (short timeout to avoid blocking SSE generator)
        try:
            await asyncio.wait_for(lock.acquire(), timeout=1.0)
        except asyncio.TimeoutError:
            yield _sse_event("sync_error", {
                "error": "sync_in_progress",
                "message": f"数据源 {source_type.value} 的 {data_type.value} 同步任务正在执行中",
            })
            return

        # Create task record and COMMIT to persist before launching background
        try:
            task = SyncTask(
                task_id=str(uuid.uuid4()),
                source_type=source_type,
                data_type=data_type,
                status=SyncStatus.PENDING,
            )
            task = await self.task_repo.create(task)
            await self.task_repo.session.commit()
        except Exception:
            lock.release()
            raise

        # Progress queue and SSE connection flag
        progress_queue: asyncio.Queue = asyncio.Queue()
        sse_connected = [True]  # mutable flag: [bool]

        # Launch background coroutine (it will release the lock when done)
        bg_task = asyncio.create_task(
            self._run_sync_background(
                task, source_type, data_type,
                symbol, start_date, end_date,
                progress_queue, sse_connected, lock,
            )
        )
        _background_tasks.add(bg_task)
        bg_task.add_done_callback(_background_tasks.discard)

        # Consume queue → yield SSE events
        try:
            while True:
                try:
                    item = await asyncio.wait_for(progress_queue.get(), timeout=30.0)
                except asyncio.TimeoutError:
                    # Send SSE heartbeat to keep connection alive
                    yield ": heartbeat\n\n"
                    continue

                if isinstance(item, dict) and "_done" in item:
                    # Final event (sync_completed or sync_failed)
                    yield item["event"]
                    break

                yield item

        except asyncio.CancelledError:
            # SSE client disconnected — mark flag so background task stops pushing
            sse_connected[0] = False
            logger.info(
                "SSE client disconnected for task %s, sync continues in background",
                task.task_id,
            )

    # ------------------------------------------------------------------
    # Background coroutine
    # ------------------------------------------------------------------

    async def _run_sync_background(
        self,
        task: SyncTask,
        source_type: SourceType,
        data_type: DataType,
        symbol: Optional[str],
        start_date: Optional[str],
        end_date: Optional[str],
        progress_queue: asyncio.Queue,
        sse_connected: list,   # [bool] mutable flag
        lock: asyncio.Lock,
    ):
        """Background coroutine: execute sync with an independent DB session.

        Runs the actual data sync with its own session so that SSE client
        disconnection does NOT interrupt database writes. Pushes progress
        events to the queue for the SSE generator to consume.
        """
        from app.core.database import async_session
        from app.infrastructure.repositories.mysql_sync_task_repo import MySQLSyncTaskRepository
        from app.infrastructure.repositories.mysql_stock_data_repo import MySQLStockDataRepository
        from app.infrastructure.repositories.mysql_datasource_repo import MySQLDataSourceRepository

        try:
            async with async_session() as bg_session:
                bg_task_repo = MySQLSyncTaskRepository(bg_session)
                bg_stock_data_repo = MySQLStockDataRepository(bg_session)
                bg_datasource_repo = MySQLDataSourceRepository(bg_session)

                try:
                    # Update task to RUNNING
                    task.start_time = datetime.now()
                    await bg_task_repo.update_status(
                        task.task_id, SyncStatus.RUNNING, start_time=task.start_time,
                    )
                    await bg_session.commit()

                    # Push sync_started event to SSE
                    if sse_connected[0]:
                        progress_queue.put_nowait(_sse_event("sync_started", {
                            "task_id": task.task_id,
                            "source_type": source_type.value,
                            "data_type": data_type.value,
                        }))

                    # Execute the actual data sync
                    success, fail, total = 0, 0, 0
                    async for event in self._execute_data_sync(
                        bg_stock_data_repo, bg_datasource_repo,
                        source_type, data_type, task,
                        symbol, start_date, end_date,
                    ):
                        # Parse event data for final stats
                        for line in event.split("\n"):
                            if line.startswith("data: "):
                                try:
                                    data = json.loads(line[6:])
                                    if data.get("success") is not None:
                                        success = data["success"]
                                        fail = data.get("failed", 0)
                                        total = data.get("total", 0)
                                except (json.JSONDecodeError, KeyError):
                                    pass

                        # Commit bg_session after each progress batch (every 10 records)
                        await bg_session.commit()

                        # Update task progress in DB (persists even if SSE disconnects)
                        await bg_task_repo.update_status(
                            task.task_id, SyncStatus.RUNNING,
                            processed_count=total,
                            success_count=success,
                            fail_count=fail,
                        )
                        await bg_session.commit()

                        # Push progress event to SSE queue (only if client is connected)
                        if sse_connected[0]:
                            progress_queue.put_nowait(event)

                    # Sync completed successfully
                    task.end_time = datetime.now()
                    duration_ms = int(
                        (task.end_time - (task.start_time or task.end_time)).total_seconds() * 1000
                    )

                    await bg_task_repo.update_status(
                        task.task_id, SyncStatus.COMPLETED,
                        processed_count=total,
                        success_count=success,
                        fail_count=fail,
                    )
                    await bg_session.commit()

                    progress_queue.put_nowait({
                        "_done": True,
                        "event": _sse_event("sync_completed", {
                            "task_id": task.task_id,
                            "total": total,
                            "processed": total,
                            "success": success,
                            "failed": fail,
                            "duration_ms": duration_ms,
                        }),
                    })

                    logger.info(
                        "Sync completed: source=%s type=%s total=%d success=%d failed=%d duration=%dms",
                        source_type.value, data_type.value, total, success, fail, duration_ms,
                    )

                except Exception as e:
                    logger.exception("Sync failed: source=%s type=%s", source_type.value, data_type.value)

                    # Rollback the bg session
                    try:
                        await bg_session.rollback()
                    except Exception:
                        pass

                    # Use a fresh session to update task failure status
                    # (the original session is in an uncertain state after rollback)
                    try:
                        async with async_session() as err_session:
                            err_task_repo = MySQLSyncTaskRepository(err_session)
                            await err_task_repo.update_status(
                                task.task_id, SyncStatus.FAILED,
                                error_message=str(e),
                            )
                            await err_session.commit()
                    except Exception:
                        logger.exception("Failed to update task status after sync error")

                    end_time = datetime.now()
                    duration_ms = int(
                        (end_time - (task.start_time or end_time)).total_seconds() * 1000
                    )

                    progress_queue.put_nowait({
                        "_done": True,
                        "event": _sse_event("sync_failed", {
                            "task_id": task.task_id,
                            "error": str(e),
                            "duration_ms": duration_ms,
                        }),
                    })

        except Exception as e:
            # Fatal error outside the inner try (e.g., session creation failed)
            logger.exception("Fatal error in background sync task %s", task.task_id)
            try:
                progress_queue.put_nowait({
                    "_done": True,
                    "event": _sse_event("sync_failed", {
                        "task_id": task.task_id,
                        "error": f"后台任务致命错误: {e}",
                        "duration_ms": 0,
                    }),
                })
            except Exception:
                pass
        finally:
            # Always release the lock
            lock.release()

    # ------------------------------------------------------------------
    # Actual data sync logic (parameterized repos)
    # ------------------------------------------------------------------

    async def _execute_data_sync(
        self,
        stock_data_repo: StockDataRepository,
        datasource_repo: DataSourceRepository,
        source_type: SourceType,
        data_type: DataType,
        task: SyncTask,
        symbol: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """Execute the actual data sync. Yields SSE progress events.

        Accepts repo instances as parameters so that the background
        coroutine can pass in repos backed by an independent session.
        """

        if source_type == SourceType.TUSHARE:
            from app.application.sync.tushare_client import TushareClient
            from app.core.config import settings

            config = await datasource_repo.get_by_type(SourceType.TUSHARE)
            if not config or not config.api_key:
                raise ValueError(f"Tushare API key not configured")

            # Decrypt the API key
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
                    await stock_data_repo.upsert_basic(entity)
                    success += 1
                except IntegrityError as e:
                    # 主键/唯一约束冲突 — rollback session 恢复事务状态，跳过此条
                    await stock_data_repo.session.rollback()
                    logger.warning("Duplicate entry for basic info %s: %s", raw.get("code", "?"), e)
                    fail += 1
                except Exception as e:
                    # 其他异常也要确保 session 状态可恢复
                    try:
                        await stock_data_repo.session.rollback()
                    except Exception:
                        pass
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
                    await stock_data_repo.upsert_quote(entity)
                    # Cache to Redis
                    if entity.code:
                        await redis_cache.set(
                            f"stock:quote:{entity.code}",
                            {"price": str(entity.price), "change_pct": str(entity.change_pct)},
                            ttl=300,  # 5 minutes
                        )
                    success += 1
                except IntegrityError as e:
                    await stock_data_repo.session.rollback()
                    logger.warning("Duplicate entry for quote %s: %s", raw.get("code", "?"), e)
                    fail += 1
                except Exception as e:
                    try:
                        await stock_data_repo.session.rollback()
                    except Exception:
                        pass
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
                try:
                    await stock_data_repo.upsert_daily_batch(quotes)
                except IntegrityError as e:
                    await stock_data_repo.session.rollback()
                    logger.warning("Duplicate entries in daily quote batch: %s", e)

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
                try:
                    await stock_data_repo.upsert_financial_batch(financials)
                except IntegrityError as e:
                    await stock_data_repo.session.rollback()
                    logger.warning("Duplicate entries in financial batch: %s", e)

            return

        return

    def _make_progress_yielder(self, task_id, source, data_type, total):
        """Create a closure that yields progress SSE events."""
        async def yield_progress(processed, success, fail):
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
