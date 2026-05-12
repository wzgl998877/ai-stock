from abc import ABC, abstractmethod
from typing import Optional

from app.domain.entities.radar_config import RadarConfig


class RadarConfigRepository(ABC):
    @abstractmethod
    async def get_by_user(self, user_id: str) -> Optional[RadarConfig]: ...

    @abstractmethod
    async def create(self, config: RadarConfig) -> RadarConfig: ...

    @abstractmethod
    async def update(self, config: RadarConfig) -> RadarConfig: ...
