"""MySQL MorningBriefing Repository"""

from datetime import date, timedelta
from typing import Optional, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.morning_briefing import MorningBriefing
from app.domain.repositories.morning_briefing_repo import MorningBriefingRepository
from app.infrastructure.db.models import MorningBriefingModel


def _to_entity(m: MorningBriefingModel) -> MorningBriefing:
    return MorningBriefing(
        id=m.id,
        user_id=m.user_id,
        briefing_date=m.briefing_date,
        ai_summary=m.ai_summary,
        content=m.content,
        is_read=bool(m.is_read),
        created_at=m.created_at,
    )


class MySQLMorningBriefingRepository(MorningBriefingRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, briefing: MorningBriefing) -> MorningBriefing:
        model = MorningBriefingModel(
            user_id=briefing.user_id,
            briefing_date=briefing.briefing_date,
            ai_summary=briefing.ai_summary,
            content=briefing.content,
        )
        self.session.add(model)
        await self.session.flush()
        briefing.id = model.id
        briefing.created_at = model.created_at
        return briefing

    async def get_today(self, user_id: str) -> Optional[MorningBriefing]:
        stmt = select(MorningBriefingModel).where(
            MorningBriefingModel.user_id == user_id,
            MorningBriefingModel.briefing_date == date.today(),
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def get_by_id(self, briefing_id: int) -> Optional[MorningBriefing]:
        stmt = select(MorningBriefingModel).where(MorningBriefingModel.id == briefing_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def mark_as_read(self, briefing_id: int) -> bool:
        stmt = select(MorningBriefingModel).where(MorningBriefingModel.id == briefing_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            return False
        model.is_read = 1
        await self.session.flush()
        return True

    async def list_history(self, user_id: str, days: int = 7) -> List[MorningBriefing]:
        cutoff = date.today() - timedelta(days=days)
        stmt = (
            select(MorningBriefingModel)
            .where(
                MorningBriefingModel.user_id == user_id,
                MorningBriefingModel.briefing_date >= cutoff,
            )
            .order_by(MorningBriefingModel.briefing_date.desc())
        )
        result = await self.session.execute(stmt)
        return [_to_entity(m) for m in result.scalars().all()]
