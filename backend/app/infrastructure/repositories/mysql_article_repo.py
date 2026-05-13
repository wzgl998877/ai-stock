"""MySQL Article Repository — 操作 t_analysis_article + t_article_industry + t_article_stock"""

import uuid
from typing import Optional, List, Tuple

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, defer

from app.domain.entities.article import Article, IndustryRef, StockRef
from app.domain.repositories.article_repo import ArticleRepository
from app.infrastructure.db.models import (
    AnalysisArticle as ArticleModel,
    ArticleIndustry,
    ArticleStock,
)


def _to_entity(model: ArticleModel) -> Article:
    """ORM model → Domain entity"""
    return Article(
        article_id=model.article_id,
        title=model.title,
        summary=model.summary,
        content=model.content,
        event_type=model.event_type,
        raw_input=model.raw_input,
        user_id=model.user_id,
        chain_table=model.chain_table,
        article_type=getattr(model, 'article_type', 'event'),
        analysis_data=getattr(model, 'analysis_data', None),
        status=getattr(model, 'status', 'completed'),
        industries=[
            IndustryRef(industry_code=ai.industry_code, chain_level=ai.chain_level, sentiment=ai.sentiment)
            for ai in model.article_industries
        ],
        stocks=[
            StockRef(stock_code=ast.stock_code, stock_name=ast.stock_name, sentiment=ast.sentiment)
            for ast in model.article_stocks
        ],
        create_time=model.create_time,
        update_time=model.update_time,
        deleted=model.deleted,
    )


def _to_list_entity(model: ArticleModel) -> Article:
    """列表视图专用：跳过 content/raw_input 等大文本字段"""
    return Article(
        article_id=model.article_id,
        title=model.title,
        summary=model.summary,
        content=None,
        event_type=model.event_type,
        raw_input=None,
        user_id=model.user_id,
        chain_table=model.chain_table,
        article_type=getattr(model, 'article_type', 'event'),
        analysis_data=getattr(model, 'analysis_data', None),
        status=getattr(model, 'status', 'completed'),
        industries=[
            IndustryRef(industry_code=ai.industry_code, chain_level=ai.chain_level, sentiment=ai.sentiment)
            for ai in model.article_industries
        ],
        stocks=[
            StockRef(stock_code=ast.stock_code, stock_name=ast.stock_name, sentiment=ast.sentiment)
            for ast in model.article_stocks
        ],
        create_time=model.create_time,
        update_time=model.update_time,
        deleted=model.deleted,
    )


# 列表查询公共 defer 选项：跳过大文本列
_LIST_DEFER_OPTIONS = (
    defer(ArticleModel.content),
    defer(ArticleModel.raw_input),
)


class MySQLArticleRepository(ArticleRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, article: Article) -> Article:
        model = ArticleModel(
            article_id=article.article_id or uuid.uuid4().hex,
            title=article.title,
            summary=article.summary,
            content=article.content,
            event_type=article.event_type,
            raw_input=article.raw_input,
            user_id=article.user_id,
            chain_table=article.chain_table,
            article_type=article.article_type,
            analysis_data=article.analysis_data,
            status=article.status,
        )
        self.session.add(model)

        # 写入 t_article_industry
        for ind in article.industries:
            ai = ArticleIndustry(
                id=uuid.uuid4().hex,
                article_id=model.article_id,
                industry_code=ind.industry_code,
                chain_level=ind.chain_level,
                sentiment=ind.sentiment,
            )
            self.session.add(ai)

        # 写入 t_article_stock
        for st in article.stocks:
            ast = ArticleStock(
                id=uuid.uuid4().hex,
                article_id=model.article_id,
                stock_code=st.stock_code,
                stock_name=st.stock_name,
                sentiment=st.sentiment,
            )
            self.session.add(ast)

        await self.session.flush()

        article.article_id = model.article_id
        article.create_time = model.create_time
        return article

    async def get_by_id(self, article_id: str) -> Optional[Article]:
        stmt = (
            select(ArticleModel)
            .where(
                ArticleModel.article_id == article_id,
                ArticleModel.deleted == "0",
            )
            .options(selectinload(ArticleModel.article_industries))
            .options(selectinload(ArticleModel.article_stocks))
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def list_articles(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        event_type: Optional[str] = None,
    ) -> Tuple[List[Article], int]:
        # count
        count_stmt = select(func.count()).select_from(ArticleModel).where(
            ArticleModel.user_id == user_id,
            ArticleModel.deleted == "0",
        )
        if event_type:
            count_stmt = count_stmt.where(ArticleModel.event_type == event_type)
        total = (await self.session.execute(count_stmt)).scalar() or 0

        # data — defer 大文本 + selectinload 关联数据
        stmt = (
            select(ArticleModel)
            .where(ArticleModel.user_id == user_id, ArticleModel.deleted == "0")
            .order_by(ArticleModel.create_time.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .options(*_LIST_DEFER_OPTIONS)
            .options(selectinload(ArticleModel.article_industries))
            .options(selectinload(ArticleModel.article_stocks))
        )
        if event_type:
            stmt = stmt.where(ArticleModel.event_type == event_type)
        result = await self.session.execute(stmt)
        models = result.scalars().all()

        return [_to_list_entity(m) for m in models], total

    async def list_by_industry(
        self, industry_code: str, user_id: str, page: int = 1, page_size: int = 20,
    ) -> Tuple[List[Article], int]:
        base_where = and_(
            ArticleModel.user_id == user_id,
            ArticleModel.deleted == "0",
            ArticleIndustry.industry_code == industry_code,
            ArticleIndustry.deleted == "0",
            ArticleModel.article_id == ArticleIndustry.article_id,
        )

        count_stmt = select(func.count()).select_from(ArticleModel).join(
            ArticleIndustry, ArticleModel.article_id == ArticleIndustry.article_id
        ).where(base_where)
        total = (await self.session.execute(count_stmt)).scalar() or 0

        stmt = (
            select(ArticleModel)
            .join(ArticleIndustry, ArticleModel.article_id == ArticleIndustry.article_id)
            .where(base_where)
            .order_by(ArticleModel.create_time.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .options(*_LIST_DEFER_OPTIONS)
            .options(selectinload(ArticleModel.article_industries))
            .options(selectinload(ArticleModel.article_stocks))
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()

        return [_to_list_entity(m) for m in models], total

    async def list_by_stock(
        self, stock_code: str, user_id: str, page: int = 1, page_size: int = 20,
    ) -> Tuple[List[Article], int]:
        base_where = and_(
            ArticleModel.user_id == user_id,
            ArticleModel.deleted == "0",
            ArticleStock.stock_code == stock_code,
            ArticleStock.deleted == "0",
        )

        count_stmt = select(func.count()).select_from(ArticleModel).join(
            ArticleStock, ArticleModel.article_id == ArticleStock.article_id
        ).where(base_where)
        total = (await self.session.execute(count_stmt)).scalar() or 0

        stmt = (
            select(ArticleModel)
            .join(ArticleStock, ArticleModel.article_id == ArticleStock.article_id)
            .where(base_where)
            .order_by(ArticleModel.create_time.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .options(*_LIST_DEFER_OPTIONS)
            .options(selectinload(ArticleModel.article_industries))
            .options(selectinload(ArticleModel.article_stocks))
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()

        return [_to_list_entity(m) for m in models], total

    async def delete(self, article_id: str) -> bool:
        stmt = select(ArticleModel).where(ArticleModel.article_id == article_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            return False
        model.deleted = "1"
        await self.session.flush()
        return True

    async def count_by_user(self, user_id: str) -> int:
        stmt = select(func.count()).select_from(ArticleModel).where(
            ArticleModel.user_id == user_id,
            ArticleModel.deleted == "0",
        )
        return (await self.session.execute(stmt)).scalar() or 0

    async def update_analysis_data(self, article_id: str, analysis_data: dict, status: str) -> None:
        """增量更新分析数据，并立即 commit 使外部查询可见。

        注意：此处使用 commit() 而非 flush()，是因为分析过程中需要通过轮询
        接口（/records/{id}/progress）读取中间进度，flush 的数据在事务内对外部不可见。
        即使后续分析失败，已提交的中间数据也应保留。
        """
        stmt = select(ArticleModel).where(ArticleModel.article_id == article_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        if model:
            model.analysis_data = analysis_data
            model.status = status
            await self.session.flush()
            await self.session.commit()

    async def update(self, article_id: str, **fields) -> None:
        """更新文章字段（如 title, summary, content），直接 commit 使外部可见。"""
        stmt = select(ArticleModel).where(ArticleModel.article_id == article_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        if model:
            for key, value in fields.items():
                if hasattr(model, key):
                    setattr(model, key, value)
            await self.session.flush()
            await self.session.commit()

    async def list_analysis_records(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        article_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Tuple[List[Article], int]:
        conditions = [
            ArticleModel.user_id == user_id,
            ArticleModel.deleted == "0",
        ]
        if article_type:
            conditions.append(ArticleModel.article_type == article_type)
        if status:
            conditions.append(ArticleModel.status == status)

        where = and_(*conditions)

        count_stmt = select(func.count()).select_from(ArticleModel).where(where)
        total = (await self.session.execute(count_stmt)).scalar() or 0

        stmt = (
            select(ArticleModel)
            .where(where)
            .order_by(ArticleModel.update_time.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .options(selectinload(ArticleModel.article_industries))
            .options(selectinload(ArticleModel.article_stocks))
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()

        return [_to_entity(m) for m in models], total
