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
