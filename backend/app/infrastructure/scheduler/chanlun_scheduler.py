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


async def _pull_daily_quotes(session_factory, codes: list[str], days: int = 30) -> None:
    """并发拉取日K并落库（单股失败不阻断；每股独立 session）。

    日线定时扫描的数据前置：拉取 → 清洗 → ``upsert_daily_batch`` → 清
    ``stock:daily:{code}:*`` 缓存。

    增量策略（2026-08-25 新浪 456 封禁后改造）：库中已有该股日K时，
    拉取窗口从「最近 30 自然日」缩为「库内最新日期 → 今天」，把新浪
    ``datalen`` 从 ~300 根降到个位数~几十根，大幅缩小请求体积。
    无数据时维持 30 自然日窗口（≈20 个交易日）做回补；更长缺口由手动
    「自选股批量同步」（365 天）兜底。

    降级链：新浪拉不到（空返回，含被限流）→ 腾讯日K兜底（2026-08-25）。
    """
    import asyncio as _asyncio
    from datetime import datetime as _dt, timedelta as _td

    from app.application.sync.sina_sync_client import SinaSyncClient
    from app.application.sync.sync_executor import _clear_kline_cache
    from app.domain.services.data_cleaner import clean_daily_quote
    from app.infrastructure.market.tencent_kline_client import TencentKlineClient
    from app.infrastructure.repositories.mysql_stock_data_repo import (
        MySQLStockDataRepository,
    )

    today = _dt.now().date()
    end_date = today.strftime("%Y-%m-%d")
    default_start = (today - _td(days=days)).strftime("%Y-%m-%d")
    sem = _asyncio.Semaphore(max(1, settings.chanlun_concurrency))

    async def _fetch_daily_raw(code: str, start: str, end: str) -> list[dict]:
        """新浪 → 腾讯降级。腾讯无 start/end 参数，返回后按日期窗口过滤。"""
        raw = await _asyncio.to_thread(
            SinaSyncClient().fetch_daily_quote,
            code=code, start_date=start, end_date=end, period="daily",
        )
        if raw:
            return raw
        logger.info("缠论日线拉取：新浪无数据/被限流，降级腾讯 code=%s", code)
        # 增量缺口换算条数：自然日 → 交易日近似（×5/7）+ 余量；至少 10
        gap_days = (_dt.strptime(end, "%Y-%m-%d") - _dt.strptime(start, "%Y-%m-%d")).days
        count = max(10, int(gap_days * 5 / 7) + 5)
        rows = await TencentKlineClient().fetch(code, period="daily", count=count)
        return [r for r in rows if start <= r.get("trade_date", "") <= end]

    async def pull(code: str) -> None:
        async with sem:
            # 增量窗口：库内最新日K之后 → 今天；无历史则默认窗口。
            # 不按 source 过滤：n8o9p0q1r2s3 起一天一条，任何源的数据都算数
            async with session_factory() as s:
                repo = MySQLStockDataRepository(s)
                latest = await repo.get_latest_daily_date(code, period="daily")
            start = latest.strftime("%Y-%m-%d") if latest else default_start
            raw = await _fetch_daily_raw(code, start, end_date)
            quotes = []
            for r in raw:
                try:
                    quotes.append(clean_daily_quote(r, "sina"))
                except Exception as e:
                    logger.warning("缠论日线拉取 %s 脏数据跳过: %s", code, e)
            if quotes:
                async with session_factory() as s:
                    try:
                        repo = MySQLStockDataRepository(s)
                        await repo.upsert_daily_batch(quotes)
                        await _clear_kline_cache(code, "daily")
                        await s.commit()
                    except Exception as e:
                        await s.rollback()
                        logger.warning("缠论日线拉取 %s 失败: %s", code, e)

    results = await _asyncio.gather(
        *[pull(c) for c in codes], return_exceptions=True
    )
    for code, r in zip(codes, results):
        if isinstance(r, Exception):
            logger.warning("缠论日线拉取 %s 失败: %s", code, r)


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

                # 1) 并发拉取最近 N 天日K（此前只扫不拉，数据靠手动同步，
                #    导致定时扫描长期 stale 跳过、信号出不来——对标 scan_m30 修正）
                await _pull_daily_quotes(session_factory, codes)

                # 2) 扫描计算
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

    # 微信 iLink 心跳保活：每天 08:30 / 20:30 发一条消息「使用」context_token，
    # 防其 ~24h 过期导致信号推送中断（含周末——周一盘前 token 必须活着）
    async def wechat_keepalive():
        from app.application.wechat.ilink_keepalive import build_keepalive

        uc = build_keepalive()
        if uc is None:
            return
        await uc.send()

    scheduler.add_job(
        wechat_keepalive,
        CronTrigger(hour="8,20", minute="30"),
        id="wechat_ilink_keepalive",
        replace_existing=True,
    )

    _scheduler = scheduler
    return scheduler


def get_scheduler():
    return _scheduler
