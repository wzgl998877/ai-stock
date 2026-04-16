from abc import ABC, abstractmethod
from typing import Optional, List
from app.domain.entities.reminder import Reminder


class ReminderRepository(ABC):
    @abstractmethod
    async def create(self, reminder: Reminder) -> Reminder: ...

    @abstractmethod
    async def update(self, reminder: Reminder) -> Reminder: ...

    @abstractmethod
    async def delete(self, reminder_id: str) -> bool: ...

    @abstractmethod
    async def get_by_id(self, reminder_id: str) -> Optional[Reminder]: ...

    @abstractmethod
    async def list_by_user(
        self, user_id: str, status: Optional[str] = None
    ) -> List[Reminder]: ...

    @abstractmethod
    async def find_by_title_and_user(
        self, title: str, user_id: str
    ) -> Optional[Reminder]: ...

    @abstractmethod
    async def count_pending(self, user_id: str) -> int: ...

    @abstractmethod
    async def list_due_reminders(self, days_ahead: int) -> List[Reminder]:
        """查找未来 N 天内到期的 pending 提醒"""
        ...
