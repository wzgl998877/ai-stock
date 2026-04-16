"""AI 分析路由 — SSE 流式 + 保存 + 相似检测"""

import json
import logging
from typing import AsyncGenerator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.application.dtos.analysis_dto import (
    AnalysisRequestDTO,
    SaveArticleDTO,
    SaveArticleResponseDTO,
    SimilarityRequestDTO,
    SimilarArticleDTO,
)
from app.application.use_cases.analyze_event import AnalyzeEventUseCase
from app.core.exceptions import InvalidInputError, AIServiceError, NoIndustryTagError
from app.infrastructure.ai.ai_service import AIService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


def _get_use_case(request: Request) -> AnalyzeEventUseCase:
    ai_service = request.app.state.ai_service
    return AnalyzeEventUseCase(ai_service)


async def _sse_stream(event_gen: AsyncGenerator) -> AsyncGenerator[str, None]:
    """将 async generator 中的 dict 事件转为 SSE data: ...\\n\\n 格式"""
    async for event in event_gen:
        yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


@router.post("/stream")
async def stream_analysis(body: AnalysisRequestDTO, request: Request):
    """启动 AI 事件分析，SSE 流式返回"""
    # 参数校验
    if not body.question or not body.question.strip():
        raise InvalidInputError("请输入事件描述")
    if len(body.question.strip()) < 10:
        raise InvalidInputError("描述太简短，请详细说明")

    ai_service: AIService = request.app.state.ai_service
    use_case = AnalyzeEventUseCase(ai_service)

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
async def save_article(body: SaveArticleDTO):
    """保存分析结果到知识库"""
    if not body.industry_codes:
        raise NoIndustryTagError()

    # TODO: 实现 ArticleRepository.save
    # 当前返回占位响应
    return SaveArticleResponseDTO(
        id="placeholder",
        title=body.title,
        industry_count=len(body.industry_codes),
        created_at="2026-01-01T00:00:00Z",
    )


@router.post("/similarity")
async def check_similarity(body: SimilarityRequestDTO):
    """检测相似历史文章"""
    # TODO: 实现 DetectSimilarUseCase
    return {"similar_articles": []}
