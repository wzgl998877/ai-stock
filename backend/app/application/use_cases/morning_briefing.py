"""晨报用例"""

import logging
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy import text

from app.domain.entities.morning_briefing import MorningBriefing
from app.domain.repositories.morning_briefing_repo import MorningBriefingRepository

logger = logging.getLogger(__name__)


class MorningBriefingUseCase:
    def __init__(self, briefing_repo: MorningBriefingRepository, ai_service=None):
        self.briefing_repo = briefing_repo
        self.ai_service = ai_service

    async def get_today(self, user_id: str):
        return await self.briefing_repo.get_today(user_id)

    async def get_history(self, user_id: str, days: int = 7):
        return await self.briefing_repo.list_history(user_id, days)

    async def generate_for_user(self, user_id: str, session) -> Optional[MorningBriefing]:
        """为指定用户生成今日晨报"""
        today = date.today()

        # 已生成则跳过
        existing = await self.briefing_repo.get_today(user_id)
        if existing:
            return existing

        # 获取昨日影响事件
        yesterday = datetime.combine(today - timedelta(days=1), datetime.min.time())
        today_start = datetime.combine(today, datetime.min.time())

        impact_events = []
        portfolio_overview = []
        try:
            stmt = text(
                "SELECT e.title, e.sentiment, e.importance, e.source_count, "
                "ui.matched_stocks, ui.matched_industries "
                "FROM t_user_impact ui "
                "JOIN t_impact_event e ON ui.event_id = e.event_id "
                "WHERE ui.user_id = :uid "
                "AND ui.created_at >= :start AND ui.created_at < :end "
                "ORDER BY ui.created_at DESC LIMIT 10"
            )
            result = await session.execute(stmt, {"uid": user_id, "start": yesterday, "end": today_start})
            for row in result.fetchall():
                impact_events.append({
                    "title": row[0],
                    "sentiment": row[1],
                    "importance": row[2],
                    "source_count": row[3],
                    "matched_stocks": row[4] or [],
                })

            # 获取自选股概览
            stmt2 = text(
                "SELECT wi.stock_code, wi.stock_name "
                "FROM t_watchlist_group wg "
                "JOIN t_watchlist_item wi ON wg.id = wi.group_id "
                "WHERE wg.user_id = :uid"
            )
            result2 = await session.execute(stmt2, {"uid": user_id})
            for row in result2.fetchall():
                portfolio_overview.append({
                    "code": row[0],
                    "name": row[1] or "",
                    "direction": "neutral",
                    "news_count": 0,
                })
        except Exception as e:
            logger.warning("查询晨报数据失败: %s", e)

        # 生成 AI 总结
        ai_summary = ""
        if self.ai_service and impact_events:
            try:
                event_list = "\n".join(f"- {e['title']} ({e['sentiment']})" for e in impact_events[:5])
                prompt = f"请用一句话（≤50字）总结以下事件对投资者的影响方向：\n{event_list}"
                result = await self.ai_service.generate_title_and_summary(
                    system_prompt="你是投资分析助手，请简洁总结。",
                    user_message=prompt,
                    max_tokens=100,
                )
                ai_summary = result[1] if isinstance(result, tuple) else str(result)
            except Exception as e:
                logger.warning("晨报 AI 总结生成失败: %s", e)

        if not ai_summary:
            if impact_events:
                pos = sum(1 for e in impact_events if e.get("sentiment") == "positive")
                neg = sum(1 for e in impact_events if e.get("sentiment") == "negative")
                direction = "偏利好" if pos > neg else ("偏利空" if neg > pos else "中性")
                ai_summary = f"昨日有 {len(impact_events)} 个事件影响你的自选股，整体{direction}。"
            else:
                ai_summary = "昨晚到今晨无重大事件影响你的投资。"

        content = {
            "impact_events": impact_events,
            "portfolio_overview": portfolio_overview,
            "today_focus": [],
        }

        briefing = MorningBriefing(
            user_id=user_id,
            briefing_date=today,
            ai_summary=ai_summary[:200],
            content=content,
        )
        briefing = await self.briefing_repo.create(briefing)
        return briefing
