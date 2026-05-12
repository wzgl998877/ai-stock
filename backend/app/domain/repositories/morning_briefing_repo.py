from abc import ABC, abstractmethod
from datetime import date
from typing import Optional, List

from app.domain.entities.morning_briefing import MorningBriefing


class MorningBriefingRepository(ABC):
    @abstractmethod
    async def create(self, briefing: MorningBriefing) -> MorningBriefing: ...

    @abstractmethod
    async def get_today(self, user_id: str) -> Optional[MorningBriefing]: ...

    @abstractmethod
    async def get_by_id(self, briefing_id: int) -> Optional[MorningBriefing]: ...

    @abstractmethod
    async def mark_as_read(self, briefing_id: int) -> bool: ...

    @abstractmethod
    async def list_history(self, user_id: str, days: int = 7) -> List[MorningBriefing]: ...
