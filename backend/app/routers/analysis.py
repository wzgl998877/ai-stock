"""AI 分析路由 — SSE 流式 + 保存 + 相似检测"""

import asyncio
import json
import logging
import re
import time
from typing import AsyncGenerator, List

from fastapi import APIRouter, Request, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select
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
from app.domain.repositories.stock_data_repo import StockDataRepository
from app.infrastructure.ai.ai_service import AIService
from app.infrastructure.repositories.mysql_article_repo import MySQLArticleRepository
from app.infrastructure.repositories.mysql_stock_data_repo import MySQLStockDataRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


# === 股票列表缓存 ===
# 从数据库读取后缓存到内存，避免重复查询
_stock_list_cache: list[dict] | None = None
_stock_list_cache_time: float = 0
_STOCK_LIST_CACHE_TTL = 4 * 3600  # 4小时


async def _get_stock_list(db: AsyncSession) -> list[dict]:
    """异步获取A股股票列表，优先走内存缓存，其次从数据库查询。"""
    global _stock_list_cache, _stock_list_cache_time

    now = time.time()
    if _stock_list_cache is not None and (now - _stock_list_cache_time) < _STOCK_LIST_CACHE_TTL:
        return _stock_list_cache

    try:
        repo = MySQLStockDataRepository(db)
        stocks = await repo.get_all_stocks()
        result = []
        for s in stocks:
            # 根据交易所推断市场
            market = "sh" if s.exchange in ("SH",) or s.code.startswith(("6", "9")) else "sz"
            result.append({"code": s.code, "name": s.name, "market": market})
        _stock_list_cache = result
        _stock_list_cache_time = now
        logger.info("股票列表缓存刷新（数据库），共 %d 条", len(result))
        return result
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
async def validate_stock(keyword: str, db: AsyncSession = Depends(get_db)):
    """验证股票代码/名称，返回匹配的股票列表（支持自动补全）"""
    if not keyword or not keyword.strip():
        return {"valid": False, "message": "请输入股票代码或名称"}

    keyword = keyword.strip()
    # 转义正则特殊字符
    safe_keyword = re.escape(keyword)
    pattern = re.compile(safe_keyword, re.IGNORECASE)

    # 异步获取股票列表（数据库 + 缓存）
    stocks = await _get_stock_list(db)
    if not stocks:
        return {"valid": False, "message": "数据源暂时不可用，请先同步股票基础信息"}

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


@router.get("/records")
async def list_analysis_records(
    page: int = 1,
    page_size: int = 20,
    status: str = None,
    db: AsyncSession = Depends(get_db),
):
    """获取分析记录列表"""
    # TODO: 从认证上下文获取 user_id，暂时用固定值（与 chat.py 保持一致）
    user_id = "default"

    repo = MySQLArticleRepository(db)
    articles, total = await repo.list_analysis_records(
        user_id=user_id,
        page=page,
        page_size=page_size,
        article_type="stock_analysis",
        status=status,
    )

    items = []
    for a in articles:
        ad = a.analysis_data or {}
        mode = ad.get("mode", "full")

        # 计算进度：分析师阶段 4 个 agent（full 模式）或 2 个 agent（quick 模式）
        agents = ad.get("agents", {})
        total_agents = 4 if mode == "full" else 2
        agents_done = len([k for k, v in agents.items() if isinstance(v, dict) and v.get("status") == "done"])

        items.append({
            "id": a.article_id,
            "title": a.title,
            "summary": a.summary,
            "status": a.status,
            "analysis_mode": mode,
            "stocks": [{"code": s.stock_code, "name": s.stock_name} for s in a.stocks],
            "industries": [{"code": i.industry_code} for i in a.industries],
            "progress": {
                "completed": agents_done,
                "total": total_agents,
            },
            "analysis_data": ad,
            "created_at": a.create_time.isoformat() if a.create_time else "",
            "updated_at": a.update_time.isoformat() if a.update_time else "",
        })

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items,
    }


@router.get("/records/{record_id}")
async def get_analysis_record(record_id: str, db: AsyncSession = Depends(get_db)):
    """获取单条分析记录详情"""
    repo = MySQLArticleRepository(db)
    article = await repo.get_by_id(record_id)

    if not article or article.article_type != "stock_analysis":
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="分析记录不存在")

    ad = article.analysis_data or {}
    mode = ad.get("mode", "full")

    return {
        "id": article.article_id,
        "title": article.title,
        "summary": article.summary,
        "content": article.content,
        "status": article.status,
        "analysis_mode": mode,
        "raw_input": article.raw_input,
        "stocks": [{"code": s.stock_code, "name": s.stock_name} for s in article.stocks],
        "industries": [{"code": i.industry_code} for i in article.industries],
        "analysis_data": ad,
        "created_at": article.create_time.isoformat() if article.create_time else "",
        "updated_at": article.update_time.isoformat() if article.update_time else "",
    }


@router.get("/records/{record_id}/progress")
async def get_analysis_progress(record_id: str, db: AsyncSession = Depends(get_db)):
    """获取分析进度（用于分析中断后轮询恢复）"""
    from fastapi import HTTPException
    from app.infrastructure.db.models import AnalysisArticle, ArticleStock

    stmt = select(AnalysisArticle, ArticleStock).join(
        ArticleStock, AnalysisArticle.article_id == ArticleStock.article_id, isouter=True
    ).where(
        AnalysisArticle.article_id == record_id,
        AnalysisArticle.deleted == "0",
    )
    result = await db.execute(stmt)
    rows = result.fetchall()

    if not rows:
        raise HTTPException(status_code=404, detail="分析记录不存在")

    article, _ = rows[0]
    ad = article.analysis_data or {}
    mode = ad.get("mode", "full")

    # 计算已完成阶段
    agents = ad.get("agents", {})
    agents_done = len([k for k, v in agents.items() if isinstance(v, dict) and v.get("status") == "done"])

    phases = {
        "analysts": {"done": False, "agents_done": 0, "agents_total": 2 if mode == "quick" else 4},
        "debate": {"done": False, "rounds": 0},
        "trader": {"done": False},
        "risk": {"done": False},
    }

    if mode != "quick":
        phases["analysts"]["agents_total"] = 4
        # 分析师完成判断
        expected = ["market", "fundamentals", "news", "sentiment"]
        phases["analysts"]["agents_done"] = len([k for k in expected if agents.get(k, {}).get("status") == "done"])
        phases["analysts"]["done"] = phases["analysts"]["agents_done"] >= phases["analysts"]["agents_total"]

        # 辩论完成判断
        if ad.get("debate", {}).get("rounds", 0) > 0 or ad.get("investment_plan"):
            phases["debate"]["done"] = True
            phases["debate"]["rounds"] = len(ad.get("debates", []))

        # 交易员完成判断
        if ad.get("decision", {}).get("action"):
            phases["trader"]["done"] = True

        # 风险完成判断
        if ad.get("risk_debate"):
            phases["risk"]["done"] = True
    else:
        expected = ["market", "fundamentals"]
        phases["analysts"]["agents_done"] = len([k for k in expected if agents.get(k, {}).get("status") == "done"])
        phases["analysts"]["done"] = phases["analysts"]["agents_done"] >= 2

    # 当前进行中的阶段
    current_phase = ad.get("current_phase", "analysts")

    # 决定整体状态
    if article.status == "completed":
        overall_status = "done"
    elif article.status == "stopped":
        overall_status = "stopped"
    else:
        overall_status = "running"

    return {
        "id": article.article_id,
        "status": overall_status,
        "analysis_mode": mode,
        "current_phase": current_phase,
        "phases": phases,
        "title": ad.get("title", ""),
        "summary": ad.get("summary", ""),
        "industries": ad.get("industries", []),
        "decision": ad.get("decision"),
        "debates": ad.get("debates", []),
        "agents": {k: v for k, v in agents.items() if isinstance(v, dict)},
        "stocks": [{"code": s.stock_code, "name": s.stock_name} for _, s in rows if s and s.stock_code],
        "created_at": article.create_time.isoformat() if article.create_time else "",
        "updated_at": article.update_time.isoformat() if article.update_time else "",
    }
