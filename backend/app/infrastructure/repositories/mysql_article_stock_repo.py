"""MySQL Repository implementation for article-stock relation (文章-股票关联)."""

from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.repositories.article_stock_repo import ArticleStockInfo, ArticleStockRepository
from app.infrastructure.db.models import ArticleStock, AnalysisArticle


class MySQLArticleStockRepository(ArticleStockRepository):
    """MySQL implementation of ArticleStockRepository"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_stock(self, stock_code: str, limit: int = 50) -> List[ArticleStockInfo]:
        """根据股票代码查询关联文章"""
        stmt = (
            select(ArticleStock, AnalysisArticle)
            .join(AnalysisArticle, ArticleStock.article_id == AnalysisArticle.article_id)
            .where(
                ArticleStock.stock_code == stock_code,
                AnalysisArticle.deleted == "0",
            )
            .order_by(AnalysisArticle.create_time.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        rows = result.all()

        infos = []
        for article_stock, article in rows:
            info = ArticleStockInfo(
                article_id=article_stock.article_id,
                stock_code=article_stock.stock_code,
                stock_name=article_stock.stock_name,
                title=article.title,
                summary=article.summary,
                saved_at=article.create_time,
            )
            infos.append(info)
        return infos

    async def get_by_article(self, article_id: str) -> List[ArticleStockInfo]:
        """根据文章ID查询关联股票"""
        stmt = (
            select(ArticleStock)
            .where(ArticleStock.article_id == article_id)
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()

        return [
            ArticleStockInfo(
                article_id=m.article_id,
                stock_code=m.stock_code,
                stock_name=m.stock_name,
            )
            for m in models
        ]
