"""MySQL Search Repository — FULLTEXT + ngram 搜索"""

from typing import List, Tuple
from sqlalchemy import select, func, and_, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.entities.article import Article
from app.domain.repositories.search_repo import SearchRepository
from app.infrastructure.db.models import (
    AnalysisArticle as ArticleModel,
    ArticleIndustry,
    ArticleStock,
)
from app.infrastructure.repositories.mysql_article_repo import _to_entity


class MySQLSearchRepository(SearchRepository):
    def __init__(self, session):
        self.session = session

    async def search(
        self, query: str, user_id: str, page: int = 1, page_size: int = 20,
    ) -> Tuple[List[Article], int]:
        match_clause = text(
            "MATCH(a.title, a.summary, a.content) AGAINST(:q IN BOOLEAN MODE)"
        )

        count_stmt = (
            select(func.count())
            .select_from(ArticleModel)
            .where(
                ArticleModel.user_id == user_id,
                ArticleModel.deleted == "0",
                match_clause,
            )
        )
        total = (await self.session.execute(count_stmt, {"q": query})).scalar() or 0

        stmt = (
            select(ArticleModel)
            .where(
                ArticleModel.user_id == user_id,
                ArticleModel.deleted == "0",
                match_clause,
            )
            .order_by(ArticleModel.create_time.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.session.execute(stmt, {"q": query})
        models = result.scalars().all()

        articles = []
        for m in models:
            full = (
                await self.session.execute(
                    select(ArticleModel)
                    .where(ArticleModel.article_id == m.article_id)
                    .options(selectinload(ArticleModel.article_industries))
                    .options(selectinload(ArticleModel.article_stocks))
                )
            ).scalar_one()
            articles.append(_to_entity(full))
        return articles, total

    async def search_by_industry(
        self, query: str, industry_code: str, user_id: str, page: int = 1, page_size: int = 20,
    ) -> Tuple[List[Article], int]:
        match_clause = text(
            "MATCH(a.title, a.summary, a.content) AGAINST(:q IN BOOLEAN MODE)"
        )
        # TODO: implement with JOIN
        return await self.search(query, user_id, page, page_size)

    async def search_by_stock(
        self, query: str, stock_code: str, user_id: str, page: int = 1, page_size: int = 20,
    ) -> Tuple[List[Article], int]:
        # TODO: implement with JOIN
        return await self.search(query, user_id, page, page_size)
