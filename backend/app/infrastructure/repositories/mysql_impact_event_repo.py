"""MySQL ImpactEvent Repository"""

from datetime import datetime, timedelta
from typing import Optional, List

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.impact_event import ImpactEvent
from app.domain.repositories.impact_event_repo import ImpactEventRepository
from app.infrastructure.db.models import ImpactEventModel


def _to_entity(m: ImpactEventModel) -> ImpactEvent:
    return ImpactEvent(
        event_id=m.event_id,
        title=m.title,
        summary=m.summary,
        event_type=m.event_type,
        sentiment=m.sentiment,
        importance=m.importance,
        affected_industries=m.affected_industries,
        affected_stocks=m.affected_stocks,
        source_count=m.source_count,
        first_seen_at=m.first_seen_at,
        last_seen_at=m.last_seen_at,
        is_active=bool(m.is_active),
        created_at=m.created_at,
    )


class MySQLImpactEventRepository(ImpactEventRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, event: ImpactEvent) -> ImpactEvent:
        model = ImpactEventModel(
            title=event.title,
            summary=event.summary,
            event_type=event.event_type,
            sentiment=event.sentiment,
            importance=event.importance,
            affected_industries=event.affected_industries,
            affected_stocks=event.affected_stocks,
            source_count=event.source_count,
            first_seen_at=event.first_seen_at or datetime.now(),
            last_seen_at=event.last_seen_at or datetime.now(),
            is_active=1 if event.is_active else 0,
        )
        self.session.add(model)
        await self.session.flush()
        event.event_id = model.event_id
        event.created_at = model.created_at
        return event

    async def update(self, event: ImpactEvent) -> ImpactEvent:
        stmt = select(ImpactEventModel).where(ImpactEventModel.event_id == event.event_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one()
        model.summary = event.summary
        model.sentiment = event.sentiment
        model.importance = event.importance
        model.affected_industries = event.affected_industries
        model.affected_stocks = event.affected_stocks
        model.source_count = event.source_count
        model.last_seen_at = datetime.now()
        model.is_active = 1 if event.is_active else 0
        await self.session.flush()
        return event

    async def get_by_id(self, event_id: int) -> Optional[ImpactEvent]:
        stmt = select(ImpactEventModel).where(ImpactEventModel.event_id == event_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def get_active_events(self, since: Optional[datetime] = None) -> List[ImpactEvent]:
        stmt = select(ImpactEventModel).where(ImpactEventModel.is_active == 1)
        if since:
            stmt = stmt.where(ImpactEventModel.first_seen_at >= since)
        stmt = stmt.order_by(ImpactEventModel.first_seen_at.desc())
        result = await self.session.execute(stmt)
        return [_to_entity(m) for m in result.scalars().all()]

    async def get_by_ids(self, event_ids: List[int]) -> List[ImpactEvent]:
        if not event_ids:
            return []
        stmt = select(ImpactEventModel).where(ImpactEventModel.event_id.in_(event_ids))
        result = await self.session.execute(stmt)
        return [_to_entity(m) for m in result.scalars().all()]

    async def archive_old_events(self, hours: int = 24) -> int:
        cutoff = datetime.now() - timedelta(hours=hours)
        stmt = select(ImpactEventModel).where(
            ImpactEventModel.is_active == 1,
            ImpactEventModel.last_seen_at < cutoff,
        )
        result = await self.session.execute(stmt)
        count = 0
        for model in result.scalars().all():
            model.is_active = 0
            count += 1
        await self.session.flush()
        return count
