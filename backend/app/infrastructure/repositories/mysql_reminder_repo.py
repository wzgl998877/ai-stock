"""MySQL Reminder Repository — CRUD + 4 阶段状态"""

import uuid
from datetime import date
from typing import Optional, List

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.reminder import Reminder
from app.domain.repositories.reminder_repo import ReminderRepository
from app.infrastructure.db.models import EventReminder as ReminderModel


def _to_entity(model: ReminderModel) -> Reminder:
    return Reminder(
        reminder_id=model.reminder_id,
        title=model.title,
        event_date=model.event_date,
        user_id=model.user_id,
        status=model.status,
        industry_tags=model.industry_tags,
        create_time=model.create_time,
        update_time=model.update_time,
        deleted=model.deleted,
    )


class MySQLReminderRepository(ReminderRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, reminder: Reminder) -> Reminder:
        model = ReminderModel(
            reminder_id=reminder.reminder_id or uuid.uuid4().hex,
            title=reminder.title,
            event_date=reminder.event_date,
            user_id=reminder.user_id,
            industry_tags=reminder.industry_tags,
            status=reminder.status,
        )
        self.session.add(model)
        await self.session.flush()
        reminder.reminder_id = model.reminder_id
        reminder.create_time = model.create_time
        return reminder

    async def update(self, reminder: Reminder) -> Reminder:
        stmt = select(ReminderModel).where(ReminderModel.reminder_id == reminder.reminder_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one()
        model.title = reminder.title
        model.event_date = reminder.event_date
        model.industry_tags = reminder.industry_tags
        model.status = reminder.status
        await self.session.flush()
        return reminder

    async def delete(self, reminder_id: str) -> bool:
        stmt = select(ReminderModel).where(ReminderModel.reminder_id == reminder_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            return False
        model.deleted = "1"
        await self.session.flush()
        return True

    async def get_by_id(self, reminder_id: str) -> Optional[Reminder]:
        stmt = select(ReminderModel).where(
            ReminderModel.reminder_id == reminder_id,
            ReminderModel.deleted == "0",
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def list_by_user(
        self, user_id: str, status: Optional[str] = None
    ) -> List[Reminder]:
        stmt = select(ReminderModel).where(
            ReminderModel.user_id == user_id,
            ReminderModel.deleted == "0",
        )
        if status:
            stmt = stmt.where(ReminderModel.status == status)
        stmt = stmt.order_by(ReminderModel.event_date.asc())
        result = await self.session.execute(stmt)
        return [_to_entity(m) for m in result.scalars().all()]

    async def find_by_title_and_user(self, title: str, user_id: str) -> Optional[Reminder]:
        stmt = select(ReminderModel).where(
            ReminderModel.title == title,
            ReminderModel.user_id == user_id,
            ReminderModel.deleted == "0",
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def count_pending(self, user_id: str) -> int:
        stmt = select(func.count()).select_from(ReminderModel).where(
            ReminderModel.user_id == user_id,
            ReminderModel.deleted == "0",
            ReminderModel.status.in_(["pending", "reminded_3day", "reminded_today"]),
        )
        return (await self.session.execute(stmt)).scalar() or 0

    async def list_due_reminders(self, days_ahead: int) -> List[Reminder]:
        from datetime import timedelta
        today = date.today()
        target = today + timedelta(days=days_ahead)
        stmt = select(ReminderModel).where(
            ReminderModel.deleted == "0",
            ReminderModel.status == "pending",
            ReminderModel.event_date <= target,
        )
        result = await self.session.execute(stmt)
        return [_to_entity(m) for m in result.scalars().all()]
