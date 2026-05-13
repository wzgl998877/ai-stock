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
        """采集并处理财经新闻"""
        logger.info("事件采集任务开始")
        try:
            from app.infrastructure.crawler.cls_provider import ClsProvider
            from app.domain.services.impact_assessment import assess_event
            from app.domain.services.event_dedup import url_hash
            from app.infrastructure.repositories.mysql_impact_event_repo import MySQLImpactEventRepository
            from app.infrastructure.repositories.mysql_impact_article_repo import MySQLImpactArticleRepository
            from app.infrastructure.repositories.mysql_user_impact_repo import MySQLUserImpactRepository
            from app.domain.entities.user_impact import UserImpact

            provider = ClsProvider()
            articles = await provider.fetch_latest(limit=50)

            if not articles:
                logger.info("未采集到新文章")
                return

            async with session_factory() as session:
                event_repo = MySQLImpactEventRepository(session)
                article_repo = MySQLImpactArticleRepository(session)
                impact_repo = MySQLUserImpactRepository(session)

                existing_hashes = set()
                existing_titles = []
                new_events = []

                processed = 0
                for article in articles:
                    result = assess_event(
                        title=article.title,
                        content=article.content,
                        source_url=article.url,
                        existing_url_hashes=existing_hashes,
                        existing_titles=existing_titles,
                    )
                    if not result:
                        continue

                    from app.domain.entities.impact_event import ImpactEvent
                    event = ImpactEvent(
                        title=result["title"],
                        summary=result["summary"],
                        sentiment=result["sentiment"],
                        importance=result["importance"],
                        affected_stocks=result["affected_stocks"],
                        affected_industries=result["affected_industries"],
                        source_count=1,
                        first_seen_at=datetime.now(),
                        last_seen_at=datetime.now(),
                    )
                    event = await event_repo.create(event)

                    from app.domain.entities.impact_article import ImpactArticle
                    impact_article = ImpactArticle(
                        event_id=event.event_id,
                        title=article.title,
                        content=article.content[:500],
                        source=article.source,
                        url=article.url,
                        url_hash=result["url_hash"] or url_hash(article.url),
                        published_at=article.published_at,
                    )
                    await article_repo.create(impact_article)

                    existing_hashes.add(impact_article.url_hash)
                    existing_titles.append(article.title)
                    new_events.append(event)
                    processed += 1

                # 将事件匹配到用户
                if new_events:
                    from sqlalchemy import text
                    stmt = text(
                        "SELECT wg.user_id, wi.stock_code "
                        "FROM t_watchlist_group wg "
                        "JOIN t_watchlist_item wi ON wg.id = wi.group_id"
                    )
                    r = await session.execute(stmt)
                    user_stocks: dict = {}
                    for row in r.fetchall():
                        user_stocks.setdefault(row[0], set()).add(row[1])

                    importance_priority = {"high": "P1", "medium": "P2", "low": "P3"}
                    matched_count = 0
                    if user_stocks:
                        for ev in new_events:
                            ev_codes = set(
                                s.get("code", "")
                                for s in (ev.affected_stocks or [])
                                if s.get("code")
                            )
                            for uid, watch_codes in user_stocks.items():
                                overlap = ev_codes & watch_codes
                                pri = importance_priority.get(ev.importance or "low", "P3")
                                if overlap:
                                    ms = [{"code": c, "direction": ev.sentiment or "neutral"} for c in overlap]
                                elif ev.importance in ("high", "medium"):
                                    ms = ev.affected_stocks or []
                                    pri = "P3"
                                else:
                                    continue

                                existing = await impact_repo.get_by_user_and_event(uid, ev.event_id)
                                if existing:
                                    continue
                                await impact_repo.create(UserImpact(
                                    user_id=uid,
                                    event_id=ev.event_id,
                                    matched_stocks=ms,
                                    matched_industries=ev.affected_industries or [],
                                    priority=pri,
                                ))
                                matched_count += 1
                    logger.info("用户影响匹配完成: %d 条记录", matched_count)

                await session.commit()
                logger.info("事件采集完成: 采集 %d 条，新增 %d 条", len(articles), processed)

        except Exception as e:
            logger.error("事件采集任务失败: %s", e, exc_info=True)

    async def generate_morning_briefing():
        """为所有有自选股的用户生成晨报"""
        logger.info("晨报生成任务开始")
        try:
            # TODO: 实现晨报生成逻辑（Phase 8）
            pass
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
