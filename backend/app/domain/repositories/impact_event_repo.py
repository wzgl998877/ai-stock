from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, List

from app.domain.entities.impact_event import ImpactEvent


class ImpactEventRepository(ABC):
    @abstractmethod
    async def create(self, event: ImpactEvent) -> ImpactEvent: ...

    @abstractmethod
    async def update(self, event: ImpactEvent) -> ImpactEvent: ...

    @abstractmethod
    async def get_by_id(self, event_id: int) -> Optional[ImpactEvent]: ...

    @abstractmethod
    async def get_active_events(self, since: Optional[datetime] = None) -> List[ImpactEvent]: ...

    @abstractmethod
    async def get_by_ids(self, event_ids: List[int]) -> List[ImpactEvent]: ...

    @abstractmethod
    async def archive_old_events(self, hours: int = 24) -> int: ...
