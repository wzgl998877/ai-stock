"""事件采集调度器 — APScheduler 集成"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)

_scheduler = None


def setup_scheduler(session_factory, ai_service=None, search_service=None):
    """初始化并返回 APScheduler 实例（不自动启动）"""
    global _scheduler

    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        logger.warning("apscheduler 未安装，事件采集调度器未启用")
        return None

    scheduler = AsyncIOScheduler()

    async def crawl_and_process():
        """采集并处理财经新闻（委托给 EventRadarUseCase）"""
        logger.info("事件采集任务开始")
        try:
            from app.infrastructure.repositories.mysql_impact_event_repo import MySQLImpactEventRepository
            from app.infrastructure.repositories.mysql_impact_article_repo import MySQLImpactArticleRepository
            from app.infrastructure.repositories.mysql_user_impact_repo import MySQLUserImpactRepository
            from app.application.use_cases.event_radar import EventRadarUseCase

            async with session_factory() as session:
                uc = EventRadarUseCase(
                    event_repo=MySQLImpactEventRepository(session),
                    article_repo=MySQLImpactArticleRepository(session),
                    impact_repo=MySQLUserImpactRepository(session),
                )
                result = await uc.crawl_and_process()
                await session.commit()
                logger.info("事件采集完成: 采集 %d 条，新增 %d 条", result.get("crawled", 0), result.get("new_events", 0))

        except Exception as e:
            logger.error("事件采集任务失败: %s", e, exc_info=True)

    async def generate_morning_briefing():
        """为所有有自选股的用户生成晨报"""
        logger.info("晨报生成任务开始")
        try:
            from sqlalchemy import text as sql_text
            from app.infrastructure.repositories.mysql_morning_briefing_repo import MySQLMorningBriefingRepository
            from app.application.use_cases.morning_briefing import MorningBriefingUseCase

            async with session_factory() as session:
                # 获取所有有自选股的用户
                stmt = sql_text("SELECT DISTINCT wg.user_id FROM t_watchlist_group wg")
                result = await session.execute(stmt)
                user_ids = [row[0] for row in result.fetchall()]

                briefing_repo = MySQLMorningBriefingRepository(session)
                uc = MorningBriefingUseCase(briefing_repo=briefing_repo, ai_service=ai_service)

                generated = 0
                for uid in user_ids:
                    try:
                        briefing = await uc.generate_for_user(uid, session)
                        if briefing:
                            generated += 1
                    except Exception as e:
                        logger.warning("用户 %s 晨报生成失败: %s", uid, e)

                await session.commit()
                logger.info("晨报生成完成: %d/%d 个用户", generated, len(user_ids))

        except Exception as e:
            logger.error("晨报生成任务失败: %s", e, exc_info=True)

    # 交易时段每10分钟采集（工作日 9:00-15:00）
    scheduler.add_job(
        crawl_and_process,
        CronTrigger(day_of_week="mon-fri", hour="9-14", minute="*/10"),
        id="crawl_trading",
        replace_existing=True,
    )

    # 非交易时段每1小时采集
    scheduler.add_job(
        crawl_and_process,
        CronTrigger(hour="*/1", minute=7),
        id="crawl_off_hours",
        replace_existing=True,
    )

    # 每天6:30生成晨报
    scheduler.add_job(
        generate_morning_briefing,
        CronTrigger(hour=6, minute=30),
        id="morning_briefing",
        replace_existing=True,
    )

    _scheduler = scheduler
    return scheduler


def get_scheduler():
    return _scheduler
