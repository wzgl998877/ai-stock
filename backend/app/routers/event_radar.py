"""事件雷达路由"""

import logging
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user
from app.infrastructure.repositories.mysql_impact_event_repo import MySQLImpactEventRepository
from app.infrastructure.repositories.mysql_impact_article_repo import MySQLImpactArticleRepository
from app.infrastructure.repositories.mysql_user_impact_repo import MySQLUserImpactRepository
from app.infrastructure.repositories.mysql_user_alert_repo import MySQLUserAlertRepository
from app.infrastructure.repositories.mysql_morning_briefing_repo import MySQLMorningBriefingRepository
from app.infrastructure.repositories.mysql_radar_config_repo import MySQLRadarConfigRepository
from app.application.use_cases.event_radar import EventRadarUseCase
from app.application.use_cases.event_alert import EventAlertUseCase
from app.application.use_cases.morning_briefing import MorningBriefingUseCase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/event-radar", tags=["event-radar"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _impact_to_dict(imp, event=None, has_related_analysis=False):
    """将 UserImpact + ImpactEvent 序列化为响应 dict"""
    ev = event or {}
    return {
        "id": imp.id,
        "event_id": imp.event_id,
        "title": ev.title if ev else "",
        "summary": ev.summary if ev else None,
        "event_type": ev.event_type if ev else None,
        "sentiment": ev.sentiment if ev else None,
        "importance": ev.importance if ev else None,
        "source_count": ev.source_count if ev else 1,
        "matched_stocks": imp.matched_stocks or [],
        "matched_industries": imp.matched_industries or [],
        "priority": imp.priority,
        "is_read": imp.is_read,
        "has_ai_insight": False,
        "has_related_analysis": has_related_analysis,
        "first_seen_at": (ev.first_seen_at.isoformat() if ev and hasattr(ev, "first_seen_at") and ev.first_seen_at else None),
        "source_name": "",
        "source_url": "",
    }


# ---------------------------------------------------------------------------
# 1. 影响雷达面板
# ---------------------------------------------------------------------------

@router.get("/impacts")
async def get_impacts(
    status: str = "all",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    sentiment: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    limit = min(limit, 100)
    offset = max(offset, 0)
    uc = EventRadarUseCase(
        event_repo=MySQLImpactEventRepository(db),
        article_repo=MySQLImpactArticleRepository(db),
        impact_repo=MySQLUserImpactRepository(db),
    )
    sd = date.fromisoformat(start_date) if start_date else None
    ed = date.fromisoformat(end_date) if end_date else None
    result = await uc.get_user_impacts(
        current_user.user_id, status, sd, ed,
        sentiment=sentiment, limit=limit, offset=offset,
    )
    await db.commit()

    events_map = result["events_map"]

    impacts = [
        _impact_to_dict(imp, events_map.get(imp.event_id))
        for imp in result["impacts"]
    ]

    return {
        "impacts": impacts,
        "stats": result["stats"],
        "last_scan_at": None,
    }


@router.get("/impacts/{impact_id}")
async def get_impact_detail(
    impact_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    uc = EventRadarUseCase(
        event_repo=MySQLImpactEventRepository(db),
        article_repo=MySQLImpactArticleRepository(db),
        impact_repo=MySQLUserImpactRepository(db),
    )
    result = await uc.get_impact_detail(current_user.user_id, impact_id)
    await db.commit()

    if not result:
        raise HTTPException(status_code=404, detail="影响事件不存在")

    imp = result["impact"]
    ev = result["event"]
    articles = result["articles"]

    # 查询知识库关联分析
    related_analyses = []
    if ev:
        related_analyses = await uc._find_related_analyses(ev)

    return {
        "id": imp.id,
        "event_id": imp.event_id,
        "title": ev.title if ev else "",
        "summary": ev.summary if ev else None,
        "event_type": ev.event_type if ev else None,
        "sentiment": ev.sentiment if ev else None,
        "importance": ev.importance if ev else None,
        "source_count": ev.source_count if ev else 1,
        "matched_stocks": imp.matched_stocks or [],
        "matched_industries": imp.matched_industries or [],
        "priority": imp.priority,
        "is_read": imp.is_read,
        "first_seen_at": (ev.first_seen_at.isoformat() if ev and ev.first_seen_at else None),
        "articles": [
            {
                "article_id": a.article_id,
                "title": a.title,
                "content": a.content,
                "source": a.source,
                "url": a.url,
                "published_at": a.published_at.isoformat() if a.published_at else None,
            }
            for a in articles
        ],
        "ai_insight": None,
        "has_related_analysis": len(related_analyses) > 0,
        "related_analyses": related_analyses,
    }


@router.get("/stats")
async def get_stats(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    uc = EventRadarUseCase(
        event_repo=MySQLImpactEventRepository(db),
        article_repo=MySQLImpactArticleRepository(db),
        impact_repo=MySQLUserImpactRepository(db),
    )
    stats = await uc.get_stats(current_user.user_id)
    await db.commit()
    return stats


@router.post("/impacts/{impact_id}/ai-insight")
async def generate_ai_insight(
    impact_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    from app.infrastructure.ai.ai_service import AIService
    ai_svc = AIService()
    uc = EventRadarUseCase(
        event_repo=MySQLImpactEventRepository(db),
        article_repo=MySQLImpactArticleRepository(db),
        impact_repo=MySQLUserImpactRepository(db),
        ai_service=ai_svc,
    )
    result = await uc.generate_ai_insight(current_user.user_id, impact_id)
    await db.commit()
    if not result:
        raise HTTPException(status_code=404, detail="影响事件不存在")
    return result


# ---------------------------------------------------------------------------
# 2. 预警推送
# ---------------------------------------------------------------------------

@router.get("/alerts")
async def get_alerts(
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    alert_repo = MySQLUserAlertRepository(db)
    uc = EventAlertUseCase(alert_repo=alert_repo)
    alerts = await uc.get_unread_alerts(current_user.user_id, limit)
    await db.commit()
    return {
        "alerts": [
            {
                "id": a.id,
                "priority": a.priority,
                "title": a.title,
                "summary": a.summary,
                "user_impact_id": a.user_impact_id,
                "is_read": a.is_read,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in alerts
        ]
    }


@router.get("/alerts/unread-count")
async def get_unread_count(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    alert_repo = MySQLUserAlertRepository(db)
    count = await alert_repo.count_unread(current_user.user_id)
    await db.commit()
    return {"count": count}


@router.put("/alerts/{alert_id}/read")
async def mark_alert_read(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    alert_repo = MySQLUserAlertRepository(db)
    success = await alert_repo.mark_as_read(alert_id)
    await db.commit()
    if not success:
        raise HTTPException(status_code=404, detail="预警不存在")
    return {"success": True}


# ---------------------------------------------------------------------------
# 3. 影响晨报
# ---------------------------------------------------------------------------

@router.get("/briefing/today")
async def get_today_briefing(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    repo = MySQLMorningBriefingRepository(db)
    uc = MorningBriefingUseCase(briefing_repo=repo)
    briefing = await uc.get_today(current_user.user_id)
    await db.commit()

    if not briefing:
        raise HTTPException(status_code=404, detail="今日晨报未生成")

    return {
        "id": briefing.id,
        "briefing_date": briefing.briefing_date.isoformat() if briefing.briefing_date else "",
        "ai_summary": briefing.ai_summary,
        "content": briefing.content,
        "is_read": briefing.is_read,
        "created_at": briefing.created_at.isoformat() if briefing.created_at else None,
    }


@router.get("/briefing/history")
async def get_briefing_history(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    repo = MySQLMorningBriefingRepository(db)
    uc = MorningBriefingUseCase(briefing_repo=repo)
    briefings = await uc.get_history(current_user.user_id)
    await db.commit()
    return {
        "briefings": [
            {
                "id": b.id,
                "briefing_date": b.briefing_date.isoformat() if b.briefing_date else "",
                "ai_summary": b.ai_summary,
                "is_read": b.is_read,
            }
            for b in briefings
        ]
    }


@router.put("/briefing/{briefing_id}/read")
async def mark_briefing_read(
    briefing_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    repo = MySQLMorningBriefingRepository(db)
    success = await repo.mark_as_read(briefing_id)
    await db.commit()
    if not success:
        raise HTTPException(status_code=404, detail="晨报不存在")
    return {"success": True}


# ---------------------------------------------------------------------------
# 4. 配置
# ---------------------------------------------------------------------------

@router.get("/config")
async def get_config(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    repo = MySQLRadarConfigRepository(db)
    config = await repo.get_by_user(current_user.user_id)
    await db.commit()

    if not config:
        return {
            "focused_industries": [],
            "event_types": ["policy", "earnings", "industry", "macro", "geopolitical"],
            "alert_sensitivity": "medium",
            "quiet_hours_start": None,
            "quiet_hours_end": None,
        }

    return {
        "focused_industries": config.focused_industries or [],
        "event_types": config.event_types or [],
        "alert_sensitivity": config.alert_sensitivity,
        "quiet_hours_start": config.quiet_hours_start.isoformat() if config.quiet_hours_start else None,
        "quiet_hours_end": config.quiet_hours_end.isoformat() if config.quiet_hours_end else None,
    }


@router.put("/config")
async def update_config(
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    from app.domain.entities.radar_config import RadarConfig
    from datetime import time

    repo = MySQLRadarConfigRepository(db)
    existing = await repo.get_by_user(current_user.user_id)

    qhs = body.get("quiet_hours_start")
    qhe = body.get("quiet_hours_end")
    qhs_time = time.fromisoformat(qhs) if qhs else None
    qhe_time = time.fromisoformat(qhe) if qhe else None

    if existing:
        existing.focused_industries = body.get("focused_industries")
        existing.event_types = body.get("event_types")
        existing.alert_sensitivity = body.get("alert_sensitivity", "medium")
        existing.quiet_hours_start = qhs_time
        existing.quiet_hours_end = qhe_time
        await repo.update(existing)
    else:
        config = RadarConfig(
            user_id=current_user.user_id,
            focused_industries=body.get("focused_industries"),
            event_types=body.get("event_types"),
            alert_sensitivity=body.get("alert_sensitivity", "medium"),
            quiet_hours_start=qhs_time,
            quiet_hours_end=qhe_time,
        )
        await repo.create(config)

    await db.commit()
    return {"success": True}


# ---------------------------------------------------------------------------
# 5. 自选股影响增强
# ---------------------------------------------------------------------------

@router.get("/stock-impacts")
async def get_stock_impacts(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    uc = EventRadarUseCase(
        event_repo=MySQLImpactEventRepository(db),
        article_repo=MySQLImpactArticleRepository(db),
        impact_repo=MySQLUserImpactRepository(db),
    )
    from app.infrastructure.repositories.mysql_watchlist_repo import MySQLWatchlistRepository
    watchlist_repo = MySQLWatchlistRepository(db)
    groups = await watchlist_repo.get_groups(current_user.user_id)
    stock_codes = []
    stock_names: dict = {}
    for g in groups:
        items = await watchlist_repo.get_items(g.id)
        for item in items:
            stock_codes.append(item.stock_code)
            stock_names[item.stock_code] = item.stock_name

    impacts = await uc.get_stock_impacts(current_user.user_id, stock_codes)
    await db.commit()

    from collections import defaultdict
    stock_impact_map: dict = defaultdict(list)
    for imp in impacts:
        for s in (imp.matched_stocks or []):
            code = s.get("code", "")
            if code:
                stock_impact_map[code].append({
                    "event_title": "",
                    "direction": s.get("direction", "neutral"),
                    "confidence": s.get("confidence", 0.0),
                    "user_impact_id": imp.id,
                })

    stocks = []
    for code in stock_codes:
        imp_list = stock_impact_map.get(code, [])
        direction = "neutral"
        if imp_list:
            pos = sum(1 for i in imp_list if i["direction"] == "positive")
            neg = sum(1 for i in imp_list if i["direction"] == "negative")
            direction = "positive" if pos > neg else ("negative" if neg > pos else "neutral")

        stocks.append({
            "code": code,
            "name": stock_names.get(code, ""),
            "impact_count_24h": len(imp_list),
            "direction": direction,
            "recent_impacts": imp_list[:5],
        })

    return {"stocks": stocks}


# ---------------------------------------------------------------------------
# Admin: 手动触发采集
# ---------------------------------------------------------------------------

@router.post("/admin/crawl")
async def trigger_crawl(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    uc = EventRadarUseCase(
        event_repo=MySQLImpactEventRepository(db),
        article_repo=MySQLImpactArticleRepository(db),
        impact_repo=MySQLUserImpactRepository(db),
    )
    result = await uc.crawl_and_process()
    await db.commit()
    return result
