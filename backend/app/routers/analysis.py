"""AI 分析路由 — SSE 流式 + 保存 + 相似检测"""

import json
import logging
from typing import AsyncGenerator

from fastapi import APIRouter, Request, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.dtos.analysis_dto import (
    AnalysisRequestDTO,
    SaveArticleDTO,
    SaveArticleResponseDTO,
    SimilarityRequestDTO,
    SimilarArticleDTO,
)
from app.application.use_cases.analyze_event import AnalyzeEventUseCase
from app.application.use_cases.manage_article import SaveArticleUseCase
from app.core.database import get_db
from app.core.exceptions import InvalidInputError, AIServiceError, NoIndustryTagError
from app.infrastructure.ai.ai_service import AIService
from app.infrastructure.repositories.mysql_article_repo import MySQLArticleRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


def _get_use_case(request: Request) -> AnalyzeEventUseCase:
    ai_service = request.app.state.ai_service
    analysis_graph = getattr(request.app.state, "analysis_graph", None)
    return AnalyzeEventUseCase(ai_service, analysis_graph)


async def _sse_stream(event_gen: AsyncGenerator) -> AsyncGenerator[str, None]:
    """将 async generator 中的 dict 事件转为 SSE data: ...\\n\\n 格式"""
    async for event in event_gen:
        yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


@router.post("/stream")
async def stream_analysis(body: AnalysisRequestDTO, request: Request):
    """启动 AI 事件分析，SSE 流式返回"""
    logger.info("收到分析请求: event_type=%s, question长度=%d", body.event_type, len(body.question or ""))

    # 参数校验
    if not body.question or not body.question.strip():
        raise InvalidInputError("请输入事件描述")
    if len(body.question.strip()) < 10:
        raise InvalidInputError("描述太简短，请详细说明")

    ai_service: AIService = request.app.state.ai_service
    analysis_graph = getattr(request.app.state, "analysis_graph", None)
    use_case = AnalyzeEventUseCase(ai_service, analysis_graph)

    return StreamingResponse(
        _sse_stream(use_case.execute(body.event_type, body.question)),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/articles", status_code=201, response_model=SaveArticleResponseDTO)
async def save_article(body: SaveArticleDTO, db: AsyncSession = Depends(get_db)):
    """保存分析结果到知识库"""
    if not body.industry_codes:
        raise NoIndustryTagError()

    repo = MySQLArticleRepository(db)
    use_case = SaveArticleUseCase(repo)
    article = await use_case.execute(
        title=body.title,
        summary=body.summary,
        content=body.content,
        event_type=body.event_type,
        raw_input=body.raw_input,
        industry_codes=body.industry_codes,
        stock_refs=[{"code": s.code, "name": s.name} for s in body.stock_refs],
        chain_table=body.chain_table,
    )
    await db.commit()

    return SaveArticleResponseDTO(
        id=article.article_id,
        title=article.title,
        industry_count=len(body.industry_codes),
        created_at=article.create_time.isoformat() if article.create_time else "",
    )


@router.post("/similarity")
async def check_similarity(body: SimilarityRequestDTO):
    """检测相似历史文章"""
    # TODO: 实现 DetectSimilarUseCase
    return {"similar_articles": []}


@router.get("/validate-stock")
async def validate_stock(keyword: str):
    """验证股票代码/名称，返回股票信息"""
    if not keyword or not keyword.strip():
        return {"valid": False, "message": "请输入股票代码或名称"}

    try:
        import akshare as ak
        # 尝试通过AKShare搜索股票
        df = ak.stock_zh_a_spot_em()
        # 按代码或名称搜索
        matches = df[df["代码"].str.contains(keyword) | df["名称"].str.contains(keyword)]
        if matches.empty:
            return {"valid": False, "message": "未找到该股票，请检查代码或名称"}

        row = matches.iloc[0]
        code = str(row["代码"])
        name = str(row["名称"])
        # 判断市场
        market = "sh" if code.startswith(("6", "9")) else "sz"

        return {
            "valid": True,
            "stock_code": code,
            "stock_name": name,
            "market": market,
        }
    except ImportError:
        return {"valid": False, "message": "数据源不可用"}
    except Exception as e:
        logger.error("验证股票失败: %s", e)
        return {"valid": False, "message": f"查询失败: {str(e)}"}


@router.get("/stock-recent")
async def check_recent_analysis(stock_code: str, minutes: int = 5, db: AsyncSession = Depends(get_db)):
    """检查某只股票近期是否有分析"""
    from datetime import datetime, timedelta
    from sqlalchemy import select, and_
    from app.infrastructure.db.models import AnalysisArticle, ArticleStock

    cutoff = datetime.now() - timedelta(minutes=minutes)

    stmt = (
        select(AnalysisArticle, ArticleStock)
        .join(ArticleStock, AnalysisArticle.article_id == ArticleStock.article_id)
        .where(
            and_(
                ArticleStock.stock_code == stock_code,
                AnalysisArticle.article_type == "stock_analysis",
                AnalysisArticle.create_time >= cutoff,
                AnalysisArticle.deleted == "0",
            )
        )
        .order_by(AnalysisArticle.create_time.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    row = result.first()

    if row:
        article, stock_ref = row
        return {
            "has_recent": True,
            "article_id": article.article_id,
            "title": article.title,
            "created_at": article.create_time.isoformat() if article.create_time else "",
        }

    return {"has_recent": False}
