"""MySQL UserAlert Repository"""

from datetime import date, datetime, timedelta
from typing import List

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.user_alert import UserAlert
from app.domain.repositories.user_alert_repo import UserAlertRepository
from app.infrastructure.db.models import UserAlertModel


def _to_entity(m: UserAlertModel) -> UserAlert:
    return UserAlert(
        id=m.id,
        user_id=m.user_id,
        user_impact_id=m.user_impact_id,
        priority=m.priority,
        title=m.title,
        summary=m.summary,
        is_read=bool(m.is_read),
        created_at=m.created_at,
    )


class MySQLUserAlertRepository(UserAlertRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, alert: UserAlert) -> UserAlert:
        model = UserAlertModel(
            user_id=alert.user_id,
            user_impact_id=alert.user_impact_id,
            priority=alert.priority,
            title=alert.title,
            summary=alert.summary,
        )
        self.session.add(model)
        await self.session.flush()
        alert.id = model.id
        alert.created_at = model.created_at
        return alert

    async def get_unread_by_user(self, user_id: str, limit: int = 10) -> List[UserAlert]:
        stmt = (
            select(UserAlertModel)
            .where(UserAlertModel.user_id == user_id, UserAlertModel.is_read == 0)
            .order_by(UserAlertModel.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return [_to_entity(m) for m in result.scalars().all()]

    async def count_unread(self, user_id: str) -> int:
        stmt = select(func.count()).select_from(UserAlertModel).where(
            UserAlertModel.user_id == user_id,
            UserAlertModel.is_read == 0,
        )
        return (await self.session.execute(stmt)).scalar() or 0

    async def mark_as_read(self, alert_id: int) -> bool:
        stmt = select(UserAlertModel).where(UserAlertModel.id == alert_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            return False
        model.is_read = 1
        await self.session.flush()
        return True

    async def count_today_alerts(self, user_id: str) -> int:
        today = date.today()
        start = datetime.combine(today, datetime.min.time())
        end = datetime.combine(today + timedelta(days=1), datetime.min.time())
        stmt = select(func.count()).select_from(UserAlertModel).where(
            UserAlertModel.user_id == user_id,
            UserAlertModel.created_at >= start,
            UserAlertModel.created_at < end,
        )
        return (await self.session.execute(stmt)).scalar() or 0
