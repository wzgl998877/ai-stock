from abc import ABC, abstractmethod
from typing import Optional, List

from app.domain.entities.user_alert import UserAlert


class UserAlertRepository(ABC):
    @abstractmethod
    async def create(self, alert: UserAlert) -> UserAlert: ...

    @abstractmethod
    async def get_unread_by_user(self, user_id: str, limit: int = 10) -> List[UserAlert]: ...

    @abstractmethod
    async def count_unread(self, user_id: str) -> int: ...

    @abstractmethod
    async def mark_as_read(self, alert_id: int) -> bool: ...

    @abstractmethod
    async def count_today_alerts(self, user_id: str) -> int: ...
