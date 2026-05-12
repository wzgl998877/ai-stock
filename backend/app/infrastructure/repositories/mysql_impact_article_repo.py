"""MySQL ImpactArticle Repository"""

from typing import Optional, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.impact_article import ImpactArticle
from app.domain.repositories.impact_article_repo import ImpactArticleRepository
from app.infrastructure.db.models import ImpactArticleModel


def _to_entity(m: ImpactArticleModel) -> ImpactArticle:
    return ImpactArticle(
        article_id=m.article_id,
        event_id=m.event_id,
        title=m.title,
        content=m.content,
        source=m.source,
        url=m.url,
        url_hash=m.url_hash,
        published_at=m.published_at,
        crawled_at=m.crawled_at,
    )


class MySQLImpactArticleRepository(ImpactArticleRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, article: ImpactArticle) -> ImpactArticle:
        model = ImpactArticleModel(
            event_id=article.event_id,
            title=article.title,
            content=article.content,
            source=article.source,
            url=article.url,
            url_hash=article.url_hash,
            published_at=article.published_at,
        )
        self.session.add(model)
        await self.session.flush()
        article.article_id = model.article_id
        article.crawled_at = model.crawled_at
        return article

    async def get_by_url_hash(self, url_hash: str) -> Optional[ImpactArticle]:
        stmt = select(ImpactArticleModel).where(ImpactArticleModel.url_hash == url_hash)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def list_by_event(self, event_id: int) -> List[ImpactArticle]:
        stmt = (
            select(ImpactArticleModel)
            .where(ImpactArticleModel.event_id == event_id)
            .order_by(ImpactArticleModel.published_at.desc())
        )
        result = await self.session.execute(stmt)
        return [_to_entity(m) for m in result.scalars().all()]
