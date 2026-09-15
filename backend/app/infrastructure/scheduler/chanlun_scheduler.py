"""缠论监控扫描调度器 — APScheduler 集成（T028）。

对标 ``event_crawler_scheduler.py``：

- 日线：工作日 ``settings.chanlun_scan_daily_cron``（默认 15:40）收盘后扫描，
  另有 ``chanlun_daily_rescan_cron``（默认 18:10）兜底补扫；数据前置（拉取 +
  逐轮到位置校验）见 ``app.application.sync.daily_sync``；
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

# 定时扫描双版本（v2 主、v1 副）：数据只拉一次，两口径各自计算/落库/推送。
# 信号表靠 dedup_key 中的版本段分身、快照表靠唯一键 (code, period, algo_version)
# 分身（o9p0q1r2s3t4），互不干扰；手动/微信/网页场景由调用方显式指定版本。
_SCAN_VERSIONS = ("1.1.0", "1.0.0")

# job 参数：默认 misfire_grace_time 仅 1 秒——进程若在触发时刻前后重启，当次
# 任务会被静默丢弃（2026-09-14 事故同类的单点）。统一放宽到 1 小时并允许补齐。
_JOB_KWARGS = {
    "max_instances": 1,
    "coalesce": True,
    "misfire_grace_time": 3600,
}


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

    async def run_daily_scan() -> None:
        """日线扫描全流程：数据前置（含到位重试）→ 双版本扫描 → 补推收尾。

        15:40 主跑与 18:10 兜底补扫共用本函数。幂等：数据已到位时 ``_is_stale``
        会逐股跳过、``dedup_key`` 保证信号不重复落库，故补扫无副作用。
        """
        logger.info("缠论日线扫描任务开始")
        try:
            # 只读自选股：session 不得跨拉取/重试存活——重试最坏 40 分钟，
            # 包住整段会变成持有 MySQL 连接的 idle-in-transaction 长事务
            async with session_factory() as session:
                codes = await _all_watchlist_codes(session)
            if not codes:
                logger.info("缠论日线扫描：无自选股，跳过")
                return

            # 1) 数据前置：拉取 + 逐轮到位校验（未到位 → 等待重试）
            from app.application.sync.daily_sync import sync_daily_quotes

            result = await sync_daily_quotes(session_factory, codes)
            preflight = result.to_preflight()
            if preflight.ok:
                logger.info(
                    "缠论日线数据到位 %d/%d（期望 %s，%d 轮）",
                    len(result.in_place_codes), result.total,
                    result.expected_date, result.attempts,
                )
            else:
                # 2026-09-14 事故的教训：数据源全挂时全链路无任何告警。这里必须
                # 留下 ERROR 级痕迹，并把诊断写进 run_log（见 preflight 贯通）
                logger.error(
                    "缠论日线数据未到位 %d/%d（期望 %s），仍继续扫描（本日可能无新信号）：%s",
                    result.total - len(result.in_place_codes), result.total,
                    result.expected_date, preflight.notes[:1],
                )

            # 2) 双版本扫描（v2 主、v1 副）：数据只拉一次、判定只做一次，
            #    重试轮次不重复扫描
            for ver in _SCAN_VERSIONS:
                async with session_factory() as session:
                    monitor = _build_monitor(session, session_factory)
                    await monitor.scan(
                        "daily", user_id="system",
                        trigger_type="scheduled", stock_codes=codes,
                        algo_version=ver, preflight=preflight,
                    )
                    await session.commit()

            # 3) 收尾：补推此前未送达的信号（token 恢复后自动补上，避免漏推
            #    信号永久丢失）；失败只记 warning，不影响扫描结果
            from app.application.wechat.chanlun_signal_push import build_signal_retrier

            retrier = build_signal_retrier(session_factory)
            if retrier is not None:
                try:
                    retried = await retrier()
                    if retried:
                        logger.info("缠论信号补推：本轮尝试 %d 条未送达信号", retried)
                except Exception:
                    logger.warning("缠论信号补推失败（不影响扫描结果）", exc_info=True)
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

            # 2) 双版本扫描（v2 主、v1 副）：行情只拉一次，两口径各自计算
            for ver in _SCAN_VERSIONS:
                async with session_factory() as session:
                    monitor = _build_monitor(session, session_factory)
                    await monitor.scan(
                        "m30", user_id="system",
                        trigger_type="scheduled", stock_codes=codes,
                        algo_version=ver,
                    )
                    await session.commit()
        except Exception as e:
            logger.error("缠论 30m 扫描任务失败: %s", e, exc_info=True)

    # 日线：工作日 chanlun_scan_daily_cron
    dh, dm = _parse_cron(settings.chanlun_scan_daily_cron)
    scheduler.add_job(
        run_daily_scan,
        CronTrigger(day_of_week="mon-fri", hour=dh, minute=dm),
        id="chanlun_daily_scan",
        replace_existing=True,
        **_JOB_KWARGS,
    )

    # 日线兜底补扫：15:40 主跑 + 3 轮重试仍未到位（数据源长时间故障）时，
    # 收盘后晚些再跑一遍补齐当天信号。空串 = 关闭
    if settings.chanlun_daily_rescan_cron:
        rh, rm = _parse_cron(settings.chanlun_daily_rescan_cron)
        scheduler.add_job(
            run_daily_scan,
            CronTrigger(day_of_week="mon-fri", hour=rh, minute=rm),
            id="chanlun_daily_rescan",
            replace_existing=True,
            **_JOB_KWARGS,
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
        **_JOB_KWARGS,
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
        **_JOB_KWARGS,
    )

    _scheduler = scheduler
    return scheduler


def get_scheduler():
    return _scheduler
