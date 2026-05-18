from abc import ABC, abstractmethod
from datetime import date
from typing import Optional, List

from app.domain.entities.user_impact import UserImpact


class UserImpactRepository(ABC):
    @abstractmethod
    async def create(self, impact: UserImpact) -> UserImpact: ...

    @abstractmethod
    async def get_by_id(self, impact_id: int) -> Optional[UserImpact]: ...

    @abstractmethod
    async def get_by_user_and_event(self, user_id: str, event_id: int) -> Optional[UserImpact]: ...

    @abstractmethod
    async def list_active_by_user(self, user_id: str, limit: int = 20, offset: int = 0) -> List[UserImpact]: ...

    @abstractmethod
    async def list_by_user(self, user_id: str, *,
                           status: str = "all",
                           start_date: Optional[date] = None,
                           end_date: Optional[date] = None,
                           sentiment: Optional[str] = None,
                           limit: int = 20,
                           offset: int = 0) -> List[UserImpact]: ...

    @abstractmethod
    async def mark_as_read(self, impact_id: int) -> bool: ...

    @abstractmethod
    async def get_stats(self, user_id: str, d: date) -> dict: ...

    @abstractmethod
    async def get_stock_impacts(self, user_id: str, stock_codes: List[str]) -> List[UserImpact]: ...
