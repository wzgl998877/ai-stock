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
from app.infrastructure.repositories.mysql_stock_analysis_repo import MySQLStockAnalysisRepository

logger = logging.getLogger(__name__)


def _reconstruct_debates(details) -> list:
    """从 detail 记录中重建前端 DebateEvent 格式的辩论数据"""
    debates = []
    for d in details:
        # 从 debate_data 字段提取辩论内容
        if d.debate_data:
            dd = d.debate_data if isinstance(d.debate_data, dict) else {}
            round_num = dd.get("round", 0)
            if dd.get("bull_argument"):
                debates.append({"speaker": "bull_researcher", "round": round_num, "content": dd["bull_argument"]})
            if dd.get("bear_argument"):
                debates.append({"speaker": "bear_researcher", "round": round_num, "content": dd["bear_argument"]})
            if dd.get("risky_view"):
                debates.append({"speaker": "risky_debator", "round": round_num, "content": dd["risky_view"]})
            if dd.get("safe_view"):
                debates.append({"speaker": "safe_debator", "round": round_num, "content": dd["safe_view"]})
            if dd.get("neutral_view"):
                debates.append({"speaker": "neutral_debator", "round": round_num, "content": dd["neutral_view"]})
        # 非辩论阶段的 agent 报告也加入（research_manager, risk_judge）
        if d.phase == "debate" and d.agent_name == "research_manager" and d.full_report:
            debates.append({"speaker": d.agent_name, "round": 0, "content": d.full_report})
        if d.phase == "risk" and d.agent_name == "risk_judge" and d.full_report:
            debates.append({"speaker": d.agent_name, "round": 0, "content": d.full_report})
    return debates


router = APIRouter(prefix="/api/analysis", tags=["analysis"])


# === 股票列表缓存 ===
# 从数据库读取后缓存到内存，避免重复查询
_stock_list_cache: list[dict] | None = None
_stock_list_cache_time: float = 0
_STOCK_LIST_CACHE_TTL = 4 * 3600  # 4小时

# AKShare 网络搜索结果缓存（独立于数据库缓存）
_akshare_stock_cache: list[dict] | None = None
_akshare_stock_cache_time: float = 0


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
    """验证股票代码/名称，返回匹配的股票列表（数据库优先 + AKShare 网络兜底）。"""
    if not keyword or not keyword.strip():
        return {"valid": False, "message": "请输入股票代码或名称"}

    keyword = keyword.strip()
    # 转义正则特殊字符
    safe_keyword = re.escape(keyword)
    pattern = re.compile(safe_keyword, re.IGNORECASE)

    # ---- 第一步：从数据库（+内存缓存）搜索 ----
    stocks = await _get_stock_list(db)

    # 精确匹配优先：代码完全匹配
    exact_code = [s for s in stocks if s["code"] == keyword]
    if exact_code:
        hit = exact_code[0]
        return {
            "valid": True,
            "stock_code": hit["code"],
            "stock_name": hit["name"],
            "market": hit["market"],
            "source": "database",
        }

    # 模糊匹配：代码前缀或名称包含
    matches = []
    for s in stocks:
        if pattern.search(s["code"]) or pattern.search(s["name"]):
            matches.append(s)
        if len(matches) >= 10:
            break

    if matches:
        # 只有一个匹配时直接返回
        if len(matches) == 1:
            hit = matches[0]
            return {
                "valid": True,
                "stock_code": hit["code"],
                "stock_name": hit["name"],
                "market": hit["market"],
                "source": "database",
            }
        # 多个匹配时返回候选列表
        return {
            "valid": True,
            "multiple": True,
            "candidates": matches,
            "source": "database",
            "message": f"找到 {len(matches)} 个匹配结果",
        }

    # ---- 第二步：数据库无结果 → AKShare 网络搜索 ----
    logger.info("数据库无匹配结果，尝试 AKShare 网络搜索: %s", keyword)
    try:
        network_matches = await asyncio.to_thread(_search_akshare, keyword)
    except Exception as e:
        logger.warning("AKShare 网络搜索失败: %s", e)
        return {"valid": False, "message": "未找到该股票，请检查代码或名称"}

    if not network_matches:
        return {"valid": False, "message": "未找到该股票，请检查代码或名称"}

    # 单条直接返回
    if len(network_matches) == 1:
        hit = network_matches[0]
        return {
            "valid": True,
            "stock_code": hit["code"],
            "stock_name": hit["name"],
            "market": hit["market"],
            "source": "network",
        }

    # 多条返回候选列表
    return {
        "valid": True,
        "multiple": True,
        "candidates": network_matches,
        "source": "network",
        "message": f"通过网络搜索找到 {len(network_matches)} 个匹配结果",
    }


def _search_akshare(keyword: str) -> list[dict]:
    """同步调用 AKShare 获取全量股票列表并在内存中匹配。

    AKShare 的 stock_info_a_code_name() 返回全 A 股代码-名称对，
    缓存到进程级别变量避免重复网络请求。
    """
    global _akshare_stock_cache, _akshare_stock_cache_time

    now = time.time()
    if _akshare_stock_cache is not None and (now - _akshare_stock_cache_time) < _STOCK_LIST_CACHE_TTL:
        all_stocks = _akshare_stock_cache
    else:
        from app.application.sync.akshare_client import AKShareClient
        client = AKShareClient()
        raw = client.fetch_basic_info()  # 返回 [{"code": "000858", "name": "五粮液", ...}, ...]
        all_stocks = []
        for r in raw:
            code = r.get("code", "")
            market = "sh" if code.startswith(("6", "9")) else "sz"
            all_stocks.append({"code": code, "name": r.get("name", ""), "market": market})
        _akshare_stock_cache = all_stocks
        _akshare_stock_cache_time = now
        logger.info("AKShare 股票列表缓存刷新（网络），共 %d 条", len(all_stocks))

    # 正则模糊匹配
    safe_kw = re.escape(keyword)
    pattern = re.compile(safe_kw, re.IGNORECASE)
    matches = []
    for s in all_stocks:
        if pattern.search(s["code"]) or pattern.search(s["name"]):
            matches.append(s)
        if len(matches) >= 10:
            break
    return matches


@router.get("/stock-recent")
async def check_recent_analysis(stock_code: str, minutes: int = 5, db: AsyncSession = Depends(get_db)):
    """检查某只股票近期是否有分析"""
    repo = MySQLStockAnalysisRepository(db)
    sa = await repo.get_recent_by_stock(stock_code, user_id="default", minutes=minutes)

    if sa:
        return {
            "has_recent": True,
            "article_id": sa.analysis_id,
            "title": sa.title,
            "created_at": sa.create_time.isoformat() if sa.create_time else "",
        }

    return {"has_recent": False}


@router.get("/records")
async def list_analysis_records(
    page: int = 1,
    page_size: int = 20,
    status: str = None,
    stock_code: str = None,
    db: AsyncSession = Depends(get_db),
):
    """获取分析记录列表，支持按股票代码筛选"""
    user_id = "default"

    repo = MySQLStockAnalysisRepository(db)

    if stock_code:
        records, total = await repo.list_by_stock(
            stock_code=stock_code,
            user_id=user_id,
            page=page,
            page_size=page_size,
        )
    else:
        records, total = await repo.list_by_user(
            user_id=user_id,
            page=page,
            page_size=page_size,
            status=status,
        )

    items = []
    for sa in records:
        # 从 details 计算进度
        mode = sa.analysis_mode
        total_agents = 4 if mode == "full" else 2
        agents_done = len([d for d in sa.details if d.phase == "analysts" and d.status == "done"])

        items.append({
            "id": sa.analysis_id,
            "title": sa.title,
            "summary": sa.summary,
            "status": sa.status,
            "analysis_mode": mode,
            "stocks": [{"code": sa.stock_code, "name": sa.stock_name}],
            "industries": [{"code": c} for c in (sa.industries or [])],
            "progress": {
                "completed": agents_done,
                "total": total_agents,
            },
            "details": [
                {
                    "agent_name": d.agent_name,
                    "phase": d.phase,
                    "status": d.status,
                    "summary": d.summary or "",
                    "full_report": d.full_report or "",
                    "completed_at": d.completed_at.isoformat() if d.completed_at else None,
                }
                for d in sa.details
            ],
            "decision": {
                "action": sa.decision_action or "",
                "target_price": float(sa.target_price) if sa.target_price else 0.0,
                "stop_loss_price": float(sa.stop_loss_price) if sa.stop_loss_price else 0.0,
                "confidence": float(sa.confidence) if sa.confidence else 0.0,
                "risk_score": float(sa.risk_score) if sa.risk_score else 0.0,
                "reasoning": sa.reasoning or "",
            } if sa.decision_action else None,
            "created_at": sa.create_time.isoformat() if sa.create_time else "",
            "updated_at": sa.update_time.isoformat() if sa.update_time else "",
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
    from fastapi import HTTPException

    repo = MySQLStockAnalysisRepository(db)
    sa = await repo.get_by_id(record_id)

    if not sa:
        raise HTTPException(status_code=404, detail="分析记录不存在")

    return {
        "id": sa.analysis_id,
        "title": sa.title,
        "summary": sa.summary,
        "content": sa.full_content or "",
        "status": sa.status,
        "analysis_mode": sa.analysis_mode,
        "current_phase": sa.current_phase or "analysts",
        "raw_input": f"{sa.stock_code} {sa.stock_name}",
        "stocks": [{"code": sa.stock_code, "name": sa.stock_name}],
        "industries": [{"code": c} for c in (sa.industries or [])],
        "details": [
            {
                "agent_name": d.agent_name,
                "phase": d.phase,
                "status": d.status,
                "summary": d.summary or "",
                "full_report": d.full_report or "",
                "thinking_steps": d.thinking_steps,
                "debate_data": d.debate_data,
                "completed_at": d.completed_at.isoformat() if d.completed_at else None,
            }
            for d in sa.details
        ],
        "decision": {
            "action": sa.decision_action or "",
            "target_price": float(sa.target_price) if sa.target_price else 0.0,
            "stop_loss_price": float(sa.stop_loss_price) if sa.stop_loss_price else 0.0,
            "confidence": float(sa.confidence) if sa.confidence else 0.0,
            "risk_score": float(sa.risk_score) if sa.risk_score else 0.0,
            "reasoning": sa.reasoning or "",
        } if sa.decision_action else None,
        "created_at": sa.create_time.isoformat() if sa.create_time else "",
        "updated_at": sa.update_time.isoformat() if sa.update_time else "",
    }


@router.get("/records/{record_id}/progress")
async def get_analysis_progress(record_id: str, db: AsyncSession = Depends(get_db)):
    """获取分析进度（用于分析中断后轮询恢复）"""
    from fastapi import HTTPException

    repo = MySQLStockAnalysisRepository(db)
    sa = await repo.get_by_id(record_id)

    if not sa:
        raise HTTPException(status_code=404, detail="分析记录不存在")

    mode = sa.analysis_mode
    current_phase = sa.current_phase

    # 构建 agents 字典（从 details）
    agents = {}
    for d in sa.details:
        agents[d.agent_name] = {
            "status": d.status,
            "summary": d.summary or "",
            "full_report": d.full_report or "",
        }

    # 计算已完成阶段
    phases = {
        "analysts": {"done": False, "agents_done": 0, "agents_total": 2 if mode == "quick" else 4},
        "debate": {"done": False, "rounds": 0},
        "trader": {"done": False},
        "risk": {"done": False},
    }

    # 分析师阶段
    analyst_agents = [d for d in sa.details if d.phase == "analysts"]
    phases["analysts"]["agents_done"] = len([d for d in analyst_agents if d.status == "done"])
    phases["analysts"]["done"] = phases["analysts"]["agents_done"] >= phases["analysts"]["agents_total"]

    # 辩论阶段
    debate_agents = [d for d in sa.details if d.phase == "debate" and d.status == "done"]
    if debate_agents:
        phases["debate"]["done"] = True

    # 交易员阶段
    trader_agents = [d for d in sa.details if d.phase == "trader" and d.status == "done"]
    if trader_agents:
        phases["trader"]["done"] = True

    # 风险阶段
    risk_agents = [d for d in sa.details if d.phase == "risk" and d.status == "done"]
    if risk_agents:
        phases["risk"]["done"] = True

    # 决定整体状态
    if sa.status == "completed":
        overall_status = "done"
    elif sa.status == "stopped":
        overall_status = "stopped"
    else:
        overall_status = "running"

    return {
        "id": sa.analysis_id,
        "status": overall_status,
        "analysis_mode": mode,
        "current_phase": current_phase,
        "phases": phases,
        "title": sa.title,
        "summary": sa.summary,
        "industries": sa.industries or [],
        "decision": {
            "action": sa.decision_action or "",
            "target_price": float(sa.target_price) if sa.target_price else 0.0,
            "stop_loss_price": float(sa.stop_loss_price) if sa.stop_loss_price else 0.0,
            "confidence": float(sa.confidence) if sa.confidence else 0.0,
            "risk_score": float(sa.risk_score) if sa.risk_score else 0.0,
            "reasoning": sa.reasoning or "",
        } if sa.decision_action else None,
        "debates": _reconstruct_debates(sa.details),
        "agents": agents,
        "stocks": [{"code": sa.stock_code, "name": sa.stock_name}],
        "created_at": sa.create_time.isoformat() if sa.create_time else "",
        "updated_at": sa.update_time.isoformat() if sa.update_time else "",
    }
