"""知识库路由 — 文章列表/详情/删除 + 行业列表 + 搜索"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import JSONResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.dtos.article_dto import (
    ArticleListItemDTO,
    ArticleDetailDTO,
    ArticleListResponseDTO,
    IndustryRefDTO,
    StockRefDTO,
)
from app.application.use_cases.manage_article import (
    ListArticlesUseCase,
    GetArticleDetailUseCase,
    DeleteArticleUseCase,
)
from app.application.use_cases.search_articles import SearchArticlesUseCase
from app.core.database import get_db
from app.infrastructure.repositories.mysql_article_repo import MySQLArticleRepository
from app.infrastructure.repositories.mysql_industry_repo import MySQLIndustryRepository
from app.infrastructure.repositories.mysql_search_repo import MySQLSearchRepository
from app.infrastructure.db.models import (
    ArticleIndustry,
    ArticleStock,
    Industry as IndustryModel,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])

DEFAULT_USER_ID = "default"


def _article_to_list_item(article) -> ArticleListItemDTO:
    dto = ArticleListItemDTO(
        id=article.article_id,
        title=article.title,
        summary=article.summary,
        industries=[
            IndustryRefDTO(code=ind.industry_code, name="", chain_level=ind.chain_level)
            for ind in article.industries
        ],
        stocks=[
            StockRefDTO(code=st.stock_code, name=st.stock_name)
            for st in article.stocks
        ],
        event_type=article.event_type,
        created_at=article.create_time.isoformat() if article.create_time else "",
    )
    # 附加个股分析的结构化数据（用于历史对比）
    if hasattr(article, 'analysis_data') and article.analysis_data:
        dto.analysis_data = article.analysis_data
    return dto


@router.get("/articles", response_model=ArticleListResponseDTO)
async def list_articles(
    view: str = Query("timeline", description="视图模式"),
    industry: Optional[str] = Query(None, description="行业代码"),
    stock_code: Optional[str] = Query(None, description="股票代码"),
    article_type: Optional[str] = Query(None, description="文章类型: event/stock_analysis"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """获取知识库文章列表"""
    from app.infrastructure.db.models import AnalysisArticle as ArticleModel

    repo = MySQLArticleRepository(db)
    use_case = ListArticlesUseCase(repo)

    # 构建 base query 以支持 article_type 筛选
    articles, total = await use_case.execute(
        user_id=DEFAULT_USER_ID,
        view=view,
        industry_code=industry,
        stock_code=stock_code,
        page=page,
        page_size=page_size,
    )

    # 如果指定了 article_type，在内存中过滤（简化实现，避免大改 use_case）
    if article_type:
        articles = [a for a in articles if getattr(a, 'article_type', 'event') == article_type]
        total = len(articles)

    # 补充行业名称
    items = []
    for article in articles:
        dto = _article_to_list_item(article)
        # 查行业名称
        if article.industries:
            codes = [ind.industry_code for ind in article.industries]
            stmt = select(IndustryModel).where(
                IndustryModel.industry_code.in_(codes),
                IndustryModel.deleted == "0",
            )
            result = await db.execute(stmt)
            ind_map = {m.industry_code: m.name for m in result.scalars().all()}
            dto.industries = [
                IndustryRefDTO(code=ind.industry_code, name=ind_map.get(ind.industry_code, ""), chain_level=ind.chain_level)
                for ind in article.industries
            ]
        items.append(dto)

    return ArticleListResponseDTO(total=total, page=page, page_size=page_size, items=items)


@router.get("/articles/{article_id}")
async def get_article_detail(article_id: str, db: AsyncSession = Depends(get_db)):
    """获取文章详情"""
    repo = MySQLArticleRepository(db)
    ind_repo = MySQLIndustryRepository(db)
    use_case = GetArticleDetailUseCase(repo, ind_repo)
    article = await use_case.execute(article_id)
    if not article:
        return JSONResponse(status_code=404, content={"code": "NOT_FOUND", "message": "文章不存在"})

    # 查行业名称
    industries = []
    if article.industries:
        codes = [ind.industry_code for ind in article.industries]
        stmt = select(IndustryModel).where(
            IndustryModel.industry_code.in_(codes),
            IndustryModel.deleted == "0",
        )
        result = await db.execute(stmt)
        ind_map = {m.industry_code: m.name for m in result.scalars().all()}
        industries = [
            IndustryRefDTO(code=ind.industry_code, name=ind_map.get(ind.industry_code, ""), chain_level=ind.chain_level)
            for ind in article.industries
        ]

    return ArticleDetailDTO(
        id=article.article_id,
        title=article.title,
        summary=article.summary,
        content=article.content,
        event_type=article.event_type,
        raw_input=article.raw_input,
        industries=industries,
        stocks=[StockRefDTO(code=s.stock_code, name=s.stock_name) for s in article.stocks],
        chain_table=article.chain_table,
        created_at=article.create_time.isoformat() if article.create_time else "",
        updated_at=article.update_time.isoformat() if article.update_time else "",
    )


@router.delete("/articles/{article_id}", status_code=204)
async def delete_article(article_id: str, db: AsyncSession = Depends(get_db)):
    """软删除文章"""
    repo = MySQLArticleRepository(db)
    use_case = DeleteArticleUseCase(repo)
    deleted = await use_case.execute(article_id)
    if not deleted:
        return JSONResponse(status_code=404, content={"code": "NOT_FOUND", "message": "文章不存在"})
    await db.commit()
    return Response(status_code=204)


@router.get("/industries")
async def list_industries(db: AsyncSession = Depends(get_db)):
    """获取有文章的行业列表"""
    stmt = (
        select(
            IndustryModel.industry_code,
            IndustryModel.name,
            func.count(ArticleIndustry.article_id).label("article_count"),
        )
        .join(ArticleIndustry, IndustryModel.industry_code == ArticleIndustry.industry_code)
        .where(
            IndustryModel.deleted == "0",
            ArticleIndustry.deleted == "0",
        )
        .group_by(IndustryModel.industry_code, IndustryModel.name)
        .order_by(func.count(ArticleIndustry.article_id).desc())
    )
    result = await db.execute(stmt)
    rows = result.all()
    return {
        "industries": [
            {"code": row.industry_code, "name": row.name, "article_count": row.article_count}
            for row in rows
        ]
    }


@router.get("/watchlist-stocks")
async def list_watchlist_stocks(db: AsyncSession = Depends(get_db)):
    """获取有文章的股票列表（跨模块预留）"""
    stmt = (
        select(
            ArticleStock.stock_code,
            ArticleStock.stock_name,
            func.count(ArticleStock.article_id).label("article_count"),
        )
        .where(ArticleStock.deleted == "0")
        .group_by(ArticleStock.stock_code, ArticleStock.stock_name)
        .order_by(func.count(ArticleStock.article_id).desc())
    )
    result = await db.execute(stmt)
    rows = result.all()
    return {
        "stocks": [
            {"code": row.stock_code, "name": row.stock_name, "article_count": row.article_count}
            for row in rows
        ]
    }


@router.get("/search", response_model=ArticleListResponseDTO)
async def search_articles(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """全文搜索知识库文章"""
    repo = MySQLSearchRepository(db)
    use_case = SearchArticlesUseCase(repo)
    articles, total = await use_case.execute(
        query=q,
        user_id=DEFAULT_USER_ID,
        page=page,
        page_size=page_size,
    )

    items = []
    for article in articles:
        dto = _article_to_list_item(article)
        # 简单高亮：截取包含关键词的片段
        if q and article.content:
            idx = article.content.lower().find(q.lower())
            if idx >= 0:
                start = max(0, idx - 30)
                end = min(len(article.content), idx + len(q) + 30)
                snippet = article.content[start:end]
                dto.highlight = f"...{snippet}..."
        items.append(dto)

    return ArticleListResponseDTO(total=total, page=page, page_size=page_size, items=items)
