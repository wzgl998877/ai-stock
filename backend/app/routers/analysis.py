"""AI 分析路由 — SSE 流式 + 保存 + 相似检测"""

import asyncio
import json
import logging
import re
import time
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


# === 股票列表缓存 ===
_stock_list_cache: list[dict] | None = None
_stock_list_cache_time: float = 0
_STOCK_LIST_CACHE_TTL = 4 * 3600  # 4小时


def _get_stock_list_sync() -> list[dict]:
    """同步获取A股股票列表（仅代码+名称），优先走缓存"""
    global _stock_list_cache, _stock_list_cache_time

    now = time.time()
    if _stock_list_cache is not None and (now - _stock_list_cache_time) < _STOCK_LIST_CACHE_TTL:
        return _stock_list_cache

    try:
        import akshare as ak
        # 轻量级接口：只返回代码和名称，不拉实时行情
        df = ak.stock_info_a_code_name()
        stocks = []
        for _, row in df.iterrows():
            code = str(row.get("code", "")).strip()
            name = str(row.get("name", "")).strip()
            if code and name:
                market = "sh" if code.startswith(("6", "9")) else "sz"
                stocks.append({"code": code, "name": name, "market": market})
        _stock_list_cache = stocks
        _stock_list_cache_time = now
        logger.info("股票列表缓存刷新，共 %d 条", len(stocks))
        return stocks
    except Exception as e:
        logger.error("获取股票列表失败: %s", e)
        if _stock_list_cache is not None:
            return _stock_list_cache  # 降级使用过期缓存
        return []


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
    """验证股票代码/名称，返回匹配的股票列表（支持自动补全）"""
    if not keyword or not keyword.strip():
        return {"valid": False, "message": "请输入股票代码或名称"}

    keyword = keyword.strip()
    # 转义正则特殊字符
    safe_keyword = re.escape(keyword)
    pattern = re.compile(safe_keyword, re.IGNORECASE)

    # 异步获取股票列表（缓存+to_thread）
    stocks = await asyncio.to_thread(_get_stock_list_sync)
    if not stocks:
        return {"valid": False, "message": "数据源暂时不可用，请稍后重试"}

    # 精确匹配优先：代码完全匹配
    exact_code = [s for s in stocks if s["code"] == keyword]
    if exact_code:
        hit = exact_code[0]
        return {
            "valid": True,
            "stock_code": hit["code"],
            "stock_name": hit["name"],
            "market": hit["market"],
        }

    # 模糊匹配：代码前缀或名称包含
    matches = []
    for s in stocks:
        if pattern.search(s["code"]) or pattern.search(s["name"]):
            matches.append(s)
        if len(matches) >= 10:
            break

    if not matches:
        return {"valid": False, "message": "未找到该股票，请检查代码或名称"}

    # 只有一个匹配时直接返回
    if len(matches) == 1:
        hit = matches[0]
        return {
            "valid": True,
            "stock_code": hit["code"],
            "stock_name": hit["name"],
            "market": hit["market"],
        }

    # 多个匹配时返回候选列表
    return {
        "valid": True,
        "multiple": True,
        "candidates": matches,
        "message": f"找到 {len(matches)} 个匹配结果",
    }


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
