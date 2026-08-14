"""自选股批量同步后台编排（日K + 30m）。

对标 ``chanlun_scheduler.scan_m30`` 的「Semaphore 限并发 + 每股独立 session +
asyncio.gather + 单股失败不阻断」范式，扩展为同时拉取日K与 30m。

- 日K：``SinaSyncClient.fetch_daily_quote``（新浪，无需 token）→ ``clean_daily_quote``
  → ``upsert_daily_batch`` → ``_clear_kline_cache``（清 ``stock:daily:{code}:*``）
- 30m：直接复用 ``sync_stock_30m``（内部已 upsert + 清 ``stock:kline30m:{code}:*``）

后台任务用独立 session（``session_factory``），与请求生命周期解耦；
任务完成后通过 ``update_cb`` 回调更新 ``t_sync_task`` 记录状态。
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Awaitable, Callable, Optional

from app.application.sync.chanlun_30m_sync import sync_stock_30m
from app.application.sync.sina_sync_client import SinaSyncClient
from app.core.config import settings
from app.domain.services.data_cleaner import clean_daily_quote

logger = logging.getLogger(__name__)

# 后台任务引用（防止被 GC 回收），沿用 sync_executor 的模式
_background_tasks: set[asyncio.Task] = set()

# 日K默认拉取区间（最近 N 天）。1 年约 250 个交易日，新浪 datalen 上限 1950，单次可拉完。
DEFAULT_DAILY_DAYS = 365

# 任务状态回调签名：(task_id, status, success, fail, error_message?)
UpdateCallback = Callable[..., Awaitable[None]]


async def _sync_one_stock(
    code: str,
    session_factory,
    start_date: str,
    end_date: str,
) -> None:
    """单股同步：日K + 30m，独立 session。单股失败抛出异常供上层计数。

    单股内部任何异常都 rollback 后向上抛，由 ``launch_batch_sync`` 统一捕获计数，
    不会阻断其他股票。
    """
    # 延迟 import，避免应用启动期循环依赖
    from app.application.sync.sync_executor import _clear_kline_cache
    from app.infrastructure.repositories.mysql_stock_data_repo import (
        MySQLStockDataRepository,
    )

    async with session_factory() as s:
        repo = MySQLStockDataRepository(s)
        try:
            # 1) 日K：新浪拉取（同步库用 asyncio.to_thread 包，避免阻塞事件循环）
            client = SinaSyncClient()
            raw_list = await asyncio.to_thread(
                client.fetch_daily_quote,
                code=code,
                start_date=start_date,
                end_date=end_date,
                period="daily",
            )
            # 清洗（参照 sync_executor._execute_data_sync：逐条 try，脏数据跳过）
            quotes = []
            for raw in raw_list:
                try:
                    quotes.append(clean_daily_quote(raw, "sina"))
                except Exception as e:
                    logger.warning("自选分组同步 %s 清洗日K脏数据跳过: %s raw=%s", code, e, raw)
            if quotes:
                await repo.upsert_daily_batch(quotes)
                await _clear_kline_cache(code, "daily")

            # 2) 30m：复用现成函数（内部已 upsert + 清 stock:kline30m:{code}:* 缓存）
            await sync_stock_30m(code, repo)

            await s.commit()
        except Exception:
            await s.rollback()
            raise


def launch_batch_sync(
    task_id: str,
    codes: list[str],
    session_factory,
    update_cb: UpdateCallback,
) -> asyncio.Task:
    """启动后台批量同步任务并返回 task 引用。

    Args:
        task_id: 对应 ``t_sync_task`` 的任务 ID。
        codes: 去重后的股票代码列表。
        session_factory: ``async_sessionmaker``，每股开独立 session。
        update_cb: 任务状态回调，签名 ``update_cb(task_id, status, success=0, fail=0, error=None)``。
            status 取值 "running" / "completed" / "failed"。

    Returns:
        后台 ``asyncio.Task`` 引用（已加入 ``_background_tasks`` 防 GC）。
    """
    sem = asyncio.Semaphore(max(1, settings.chanlun_concurrency))
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=DEFAULT_DAILY_DAYS)).strftime("%Y-%m-%d")
    success = [0]
    fail = [0]

    async def pull(code: str) -> None:
        async with sem:
            try:
                await _sync_one_stock(code, session_factory, start_date, end_date)
                success[0] += 1
            except Exception as e:
                fail[0] += 1
                logger.warning("自选分组同步 %s 失败: %s", code, e)

    async def runner() -> None:
        try:
            await update_cb(task_id, "running")
            if codes:
                await asyncio.gather(*[pull(c) for c in codes])
            await update_cb(
                task_id, "completed", success=success[0], fail=fail[0],
                processed=success[0] + fail[0],
            )
        except Exception as e:
            logger.error("自选分组同步任务 %s 异常: %s", task_id, e, exc_info=True)
            await update_cb(
                task_id, "failed", success=success[0], fail=fail[0],
                processed=success[0] + fail[0], error=str(e),
            )

    bg = asyncio.create_task(runner())
    _background_tasks.add(bg)
    bg.add_done_callback(_background_tasks.discard)
    return bg
