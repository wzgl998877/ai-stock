"""缠论监控扫描调度器 — APScheduler 集成（T028）。

对标 ``event_crawler_scheduler.py``：

- 日线：工作日 ``settings.chanlun_scan_daily_cron``（默认 15:40）收盘后扫描；
- 30 分钟：八时点（10:05/10:35/11:05/11:35/13:35/14:05/14:35/15:05），每根 30m K 线
  收盘后 5 分钟——先并发拉取最新行情（``sync_stock_30m``），再扫描计算。

扫描范围：全部用户自选股并集（``t_watchlist_item`` DISTINCT stock_code）。
开关由 ``main.py`` lifespan 按 ``settings.chanlun_scan_enabled`` 控制。
"""

import asyncio
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

_scheduler = None


def _parse_cron(hhmm: str) -> tuple[int, int]:
    """``"15:40"`` → ``(15, 40)``。"""
    h, m = hhmm.split(":")
    return int(h), int(m)


async def _all_watchlist_codes(session) -> list[str]:
    """全部用户自选股并集（去重、升序）。"""
    from sqlalchemy import text as sql_text

    stmt = sql_text(
        "SELECT DISTINCT wi.stock_code FROM t_watchlist_item wi "
        "JOIN t_watchlist_group wg ON wi.group_id = wg.id "
        "WHERE wi.stock_code <> ''"
    )
    result = await session.execute(stmt)
    return sorted({row[0] for row in result.fetchall() if row[0]})


def _build_monitor(session, session_factory):
    """从主 session 装配监控 UseCase；每股计算用 session_factory 建独立 session。"""
    from app.application.use_cases.chanlun_calc import ChanlunCalcUseCase
    from app.application.use_cases.chanlun_monitor import ChanlunMonitorUseCase
    from app.application.wechat.chanlun_signal_push import build_signal_pusher
    from app.infrastructure.repositories.mysql_chanlun_repo import MySQLChanlunRepository
    from app.infrastructure.repositories.mysql_stock_data_repo import MySQLStockDataRepository
    from app.infrastructure.repositories.mysql_watchlist_repo import MySQLWatchlistRepository

    def _build_calc(s):
        return ChanlunCalcUseCase(
            stock_data_repo=MySQLStockDataRepository(s),
            chanlun_repo=MySQLChanlunRepository(s),
        )

    return ChanlunMonitorUseCase(
        watchlist_repo=MySQLWatchlistRepository(session),
        chanlun_repo=MySQLChanlunRepository(session),
        algo_version=settings.chanlun_algo_version,
        session_factory=session_factory,
        build_calc=_build_calc,
        signal_pusher=build_signal_pusher(session_factory),
    )


def setup_scheduler(session_factory):
    """初始化并返回 APScheduler 实例（不自动启动）。"""
    global _scheduler

    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.combining import OrTrigger
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        logger.warning("apscheduler 未安装，缠论扫描调度器未启用")
        return None

    scheduler = AsyncIOScheduler()

    async def scan_daily():
        logger.info("缠论日线扫描任务开始")
        try:
            async with session_factory() as session:
                codes = await _all_watchlist_codes(session)
                if not codes:
                    logger.info("缠论日线扫描：无自选股，跳过")
                    return
                monitor = _build_monitor(session, session_factory)
                await monitor.scan(
                    "daily", user_id="system",
                    trigger_type="scheduled", stock_codes=codes,
                )
                await session.commit()
        except Exception as e:
            logger.error("缠论日线扫描任务失败: %s", e, exc_info=True)

    async def scan_m30():
        logger.info("缠论 30m 扫描任务开始")
        try:
            from app.application.sync.chanlun_30m_sync import sync_stock_30m
            from app.infrastructure.repositories.mysql_stock_data_repo import (
                MySQLStockDataRepository,
            )

            async with session_factory() as session:
                codes = await _all_watchlist_codes(session)
                if not codes:
                    logger.info("缠论 30m 扫描：无自选股，跳过")
                    return

                # 1) 并发拉取最新 30m 行情（单股失败不阻断；每股独立 session）
                sem = asyncio.Semaphore(max(1, settings.chanlun_concurrency))

                async def pull(code: str):
                    async with sem:
                        async with session_factory() as s:
                            try:
                                repo = MySQLStockDataRepository(s)
                                await sync_stock_30m(code, repo)
                                await s.commit()
                            except Exception as e:
                                await s.rollback()
                                logger.warning("缠论 30m 拉取 %s 失败: %s", code, e)

                await asyncio.gather(*[pull(c) for c in codes])

                # 2) 扫描计算
                monitor = _build_monitor(session, session_factory)
                await monitor.scan(
                    "m30", user_id="system",
                    trigger_type="scheduled", stock_codes=codes,
                )
                await session.commit()
        except Exception as e:
            logger.error("缠论 30m 扫描任务失败: %s", e, exc_info=True)

    # 日线：工作日 chanlun_scan_daily_cron
    dh, dm = _parse_cron(settings.chanlun_scan_daily_cron)
    scheduler.add_job(
        scan_daily,
        CronTrigger(day_of_week="mon-fri", hour=dh, minute=dm),
        id="chanlun_daily_scan",
        replace_existing=True,
    )

    # 30m：八时点（每根收盘后 5 分钟），用 OrTrigger 组合
    m30_trigger = OrTrigger([
        CronTrigger(day_of_week="mon-fri", hour="10-11", minute="5,35"),
        CronTrigger(day_of_week="mon-fri", hour="13", minute="35"),
        CronTrigger(day_of_week="mon-fri", hour="14", minute="5,35"),
        CronTrigger(day_of_week="mon-fri", hour="15", minute="5"),
    ])
    scheduler.add_job(
        scan_m30,
        m30_trigger,
        id="chanlun_m30_scan",
        replace_existing=True,
    )

    _scheduler = scheduler
    return scheduler


def get_scheduler():
    return _scheduler
