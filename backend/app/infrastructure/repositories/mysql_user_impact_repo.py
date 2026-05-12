"""MySQL UserImpact Repository"""

from datetime import date, datetime, timedelta
from typing import Optional, List

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.user_impact import UserImpact
from app.domain.repositories.user_impact_repo import UserImpactRepository
from app.infrastructure.db.models import UserImpactModel, ImpactEventModel


def _to_entity(m: UserImpactModel) -> UserImpact:
    return UserImpact(
        id=m.id,
        user_id=m.user_id,
        event_id=m.event_id,
        matched_stocks=m.matched_stocks,
        matched_industries=m.matched_industries,
        priority=m.priority,
        is_read=bool(m.is_read),
        is_alert_sent=bool(m.is_alert_sent),
        created_at=m.created_at,
    )


class MySQLUserImpactRepository(UserImpactRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, impact: UserImpact) -> UserImpact:
        model = UserImpactModel(
            user_id=impact.user_id,
            event_id=impact.event_id,
            matched_stocks=impact.matched_stocks,
            matched_industries=impact.matched_industries,
            priority=impact.priority,
        )
        self.session.add(model)
        await self.session.flush()
        impact.id = model.id
        impact.created_at = model.created_at
        return impact

    async def get_by_id(self, impact_id: int) -> Optional[UserImpact]:
        stmt = select(UserImpactModel).where(UserImpactModel.id == impact_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def get_by_user_and_event(self, user_id: str, event_id: int) -> Optional[UserImpact]:
        stmt = select(UserImpactModel).where(
            UserImpactModel.user_id == user_id,
            UserImpactModel.event_id == event_id,
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def list_active_by_user(self, user_id: str) -> List[UserImpact]:
        stmt = (
            select(UserImpactModel)
            .join(ImpactEventModel, UserImpactModel.event_id == ImpactEventModel.event_id)
            .where(
                UserImpactModel.user_id == user_id,
                ImpactEventModel.is_active == 1,
            )
            .order_by(UserImpactModel.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return [_to_entity(m) for m in result.scalars().all()]

    async def list_archived_by_user(self, user_id: str, d: date) -> List[UserImpact]:
        start = datetime.combine(d, datetime.min.time())
        end = datetime.combine(d + timedelta(days=1), datetime.min.time())
        stmt = (
            select(UserImpactModel)
            .join(ImpactEventModel, UserImpactModel.event_id == ImpactEventModel.event_id)
            .where(
                UserImpactModel.user_id == user_id,
                ImpactEventModel.is_active == 0,
                UserImpactModel.created_at >= start,
                UserImpactModel.created_at < end,
            )
            .order_by(UserImpactModel.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return [_to_entity(m) for m in result.scalars().all()]

    async def mark_as_read(self, impact_id: int) -> bool:
        stmt = select(UserImpactModel).where(UserImpactModel.id == impact_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            return False
        model.is_read = 1
        await self.session.flush()
        return True

    async def get_stats(self, user_id: str, d: date) -> dict:
        start = datetime.combine(d, datetime.min.time())
        end = datetime.combine(d + timedelta(days=1), datetime.min.time())
        week_ago = start - timedelta(days=7)

        today_stmt = (
            select(
                func.count().label("total"),
                func.sum(
                    func.if_(ImpactEventModel.sentiment == "positive", 1, 0)
                ).label("positive"),
                func.sum(
                    func.if_(ImpactEventModel.sentiment == "negative", 1, 0)
                ).label("negative"),
                func.sum(
                    func.if_(ImpactEventModel.sentiment == "neutral", 1, 0)
                ).label("neutral"),
            )
            .select_from(UserImpactModel)
            .join(ImpactEventModel, UserImpactModel.event_id == ImpactEventModel.event_id)
            .where(
                UserImpactModel.user_id == user_id,
                UserImpactModel.created_at >= start,
                UserImpactModel.created_at < end,
            )
        )
        result = await self.session.execute(today_stmt)
        row = result.one()

        week_stmt = select(func.count()).select_from(UserImpactModel).where(
            UserImpactModel.user_id == user_id,
            UserImpactModel.created_at >= week_ago,
        )
        week_total = (await self.session.execute(week_stmt)).scalar() or 0

        return {
            "today_total": row.total or 0,
            "today_positive": int(row.positive or 0),
            "today_negative": int(row.negative or 0),
            "today_neutral": int(row.neutral or 0),
            "week_total": week_total,
        }

    async def get_stock_impacts(self, user_id: str, stock_codes: List[str]) -> List[UserImpact]:
        if not stock_codes:
            return []
        cutoff = datetime.now() - timedelta(hours=24)
        stmt = (
            select(UserImpactModel)
            .where(
                UserImpactModel.user_id == user_id,
                UserImpactModel.created_at >= cutoff,
            )
            .order_by(UserImpactModel.created_at.desc())
        )
        result = await self.session.execute(stmt)
        impacts = [_to_entity(m) for m in result.scalars().all()]
        # Filter to only those matching requested stock codes
        filtered = []
        for imp in impacts:
            stocks = imp.matched_stocks or []
            matched_codes = [s.get("code", "") for s in stocks]
            if any(c in matched_codes for c in stock_codes):
                filtered.append(imp)
        return filtered
