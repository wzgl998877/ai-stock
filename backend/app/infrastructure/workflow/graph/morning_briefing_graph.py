"""晨报 LangGraph 工作流"""

import json
import logging
from datetime import date, datetime
from typing import Any

from app.domain.entities.morning_briefing import MorningBriefing
from app.domain.repositories.morning_briefing_repo import MorningBriefingRepository
from app.domain.repositories.impact_event_repo import ImpactEventRepository
from app.domain.repositories.user_impact_repo import UserImpactRepository

logger = logging.getLogger(__name__)


def build_morning_briefing_graph(
    briefing_repo: MorningBriefingRepository,
    event_repo: ImpactEventRepository,
    impact_repo: UserImpactRepository,
    ai_service=None,
):
    """构建晨报生成工作流（简化版，不依赖 LangGraph）"""

    async def generate_for_user(user_id: str) -> MorningBriefing | None:
        """为单个用户生成晨报"""
        # 检查是否已生成
        existing = await briefing_repo.get_today(user_id)
        if existing:
            return existing

        # 收集影响事件
        impacts = await impact_repo.list_active_by_user(user_id)
        event_ids = [imp.event_id for imp in impacts]
        events = []
        if event_ids:
            events = await event_repo.get_by_ids(event_ids)

        # 构建事件摘要
        events_text = "\n".join(
            f"- {e.title} ({e.sentiment}, {e.importance})"
            for e in events[:10]
        ) if events else "暂无活跃影响事件"

        # 收集自选股概览
        stocks_text = ""
        stock_impacts = await impact_repo.get_stock_impacts(user_id, [])
        if stock_impacts:
            for imp in stock_impacts[:5]:
                for s in (imp.matched_stocks or []):
                    stocks_text += f"- {s.get('name', s.get('code', ''))}: {s.get('direction', 'neutral')}\n"

        # AI 生成晨报
        ai_summary = f"今日有 {len(events)} 个影响事件，请关注。"
        content = {
            "impact_events": [
                {
                    "event_id": e.event_id,
                    "title": e.title,
                    "sentiment": e.sentiment,
                    "matched_stocks": e.affected_stocks or [],
                    "source_count": e.source_count,
                }
                for e in events[:5]
            ],
            "portfolio_overview": [],
            "today_focus": [],
        }

        if ai_service:
            try:
                from app.infrastructure.ai.prompts.impact_assessment import MORNING_BRIEFING_PROMPT
                prompt = MORNING_BRIEFING_PROMPT.format(
                    events=events_text,
                    portfolio=stocks_text or "暂无自选股数据",
                )
                result = await ai_service.generate_title_and_summary(
                    system_prompt="你是一位专业的投资顾问，请以JSON格式输出晨报。",
                    user_message=prompt,
                    max_tokens=1024,
                )
                content_str = result[1] if isinstance(result, tuple) else str(result)
                start = content_str.find("{")
                end = content_str.rfind("}") + 1
                if start >= 0 and end > start:
                    parsed = json.loads(content_str[start:end])
                    ai_summary = parsed.get("ai_summary", ai_summary)
                    if "content" in parsed:
                        content = parsed["content"]
            except Exception as e:
                logger.warning("AI 晨报生成失败: %s", e)

        briefing = MorningBriefing(
            user_id=user_id,
            briefing_date=date.today(),
            ai_summary=ai_summary[:200],
            content=content,
        )
        return await briefing_repo.create(briefing)

    return {"generate_for_user": generate_for_user}
