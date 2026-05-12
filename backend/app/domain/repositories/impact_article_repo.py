from abc import ABC, abstractmethod
from typing import Optional, List

from app.domain.entities.impact_article import ImpactArticle


class ImpactArticleRepository(ABC):
    @abstractmethod
    async def create(self, article: ImpactArticle) -> ImpactArticle: ...

    @abstractmethod
    async def get_by_url_hash(self, url_hash: str) -> Optional[ImpactArticle]: ...

    @abstractmethod
    async def list_by_event(self, event_id: int) -> List[ImpactArticle]: ...
