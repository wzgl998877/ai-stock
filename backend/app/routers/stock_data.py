"""Stock data query API router.

Provides:
- GET /api/v1/stocks/{code}          — Stock basic info
- GET /api/v1/stocks/{code}/quote    — Latest market quote
- GET /api/v1/stocks/{code}/daily    — Historical K-line data
- GET /api/v1/stocks/{code}/financial — Financial data

All endpoints check Redis cache first, fall back to MySQL on cache miss.
"""

import json
import logging
from typing import Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.domain.repositories.stock_data_repo import StockDataRepository
from app.infrastructure.repositories.mysql_stock_data_repo import MySQLStockDataRepository
from app.infrastructure.cache.redis_cache import redis_cache

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/stocks", tags=["stock-data"])


def _get_repo(db: AsyncSession = Depends(get_db)) -> StockDataRepository:
    return MySQLStockDataRepository(db)


# -------------------------------------------------------------------
# 静态路由必须放在 /{code} 之前，否则 FastAPI 会把 "search"/"all"
# 当作路径参数 {code} 匹配，导致 404
# -------------------------------------------------------------------


@router.get("/search")
async def search_stocks(
    q: str = Query(..., description="搜索关键词"),
    limit: int = Query(20, description="最大返回数量"),
    repo: StockDataRepository = Depends(_get_repo),
):
    """模糊搜索股票（代码/名称匹配）。"""
    all_stocks = await repo.get_all_stocks()
    q_lower = q.lower()

    matched = [
        s for s in all_stocks
        if q_lower in s.code.lower() or q_lower in s.name.lower()
    ][:limit]

    items = [
        {"code": s.code, "name": s.name, "industry": getattr(s, "industry", "") or ""}
        for s in matched
    ]
    return {"data": {"query": q, "total": len(items), "items": items}}


@router.get("/all")
async def get_all_stocks(
    repo: StockDataRepository = Depends(_get_repo),
):
    """获取所有活跃股票列表。"""
    cached = redis_cache.get("stock:all")
    if cached:
        return {"data": cached}

    stocks = await repo.get_all_stocks()
    items = [
        {"code": s.code, "name": s.name, "industry": getattr(s, "industry", "") or ""}
        for s in stocks if s.is_active
    ]
    result = {"total": len(items), "items": items}
    redis_cache.set("stock:all", result, ttl=86400)
    return {"data": result}


# -------------------------------------------------------------------
# 动态路由 /{code}
# -------------------------------------------------------------------


@router.get("/{code}")
async def get_stock_basic(
    code: str,
    repo: StockDataRepository = Depends(_get_repo),
):
    """Get stock basic information (highest priority source)."""
    # Check cache
    cached = redis_cache.get(f"stock:basic:{code}")
    if cached:
        return {"data": cached}

    info = await repo.get_basic(code)
    if not info:
        raise HTTPException(status_code=404, detail=f"股票 {code} 不存在")

    result = {
        "code": info.code,
        "name": info.name,
        "exchange": info.exchange,
        "market_type": info.market_type,
        "list_date": info.list_date.isoformat() if info.list_date else None,
        "is_active": info.is_active,
        "data_source": info.data_source,
    }

    # Cache for 24 hours
    redis_cache.set(f"stock:basic:{code}", result, ttl=86400)

    return {"data": result}


@router.get("/{code}/quote")
async def get_stock_quote(
    code: str,
    repo: StockDataRepository = Depends(_get_repo),
):
    """Get latest market quote for a stock."""
    # Check cache
    cached = redis_cache.get(f"stock:quote:{code}")
    if cached:
        return {"data": cached}

    quote = await repo.get_quote(code)
    if not quote:
        raise HTTPException(status_code=404, detail=f"股票 {code} 的行情数据不存在")

    from decimal import Decimal

    result = {
        "code": quote.code,
        "price": float(quote.price) if quote.price else None,
        "change_pct": float(quote.change_pct) if quote.change_pct else None,
        "change_amount": float(quote.change_amount) if quote.change_amount else None,
        "volume": float(quote.volume) if quote.volume else None,
        "amount": float(quote.amount) if quote.amount else None,
        "open_price": float(quote.open_price) if quote.open_price else None,
        "high_price": float(quote.high_price) if quote.high_price else None,
        "low_price": float(quote.low_price) if quote.low_price else None,
        "pre_close": float(quote.pre_close) if quote.pre_close else None,
        "quote_time": quote.quote_time.isoformat() if quote.quote_time else None,
        "data_source": quote.data_source,
    }

    # Cache for 5 minutes
    redis_cache.set(f"stock:quote:{code}", result, ttl=300)

    return {"data": result}


@router.get("/{code}/daily")
async def get_stock_daily(
    code: str,
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    period: str = Query("daily", description="Period: daily/weekly/monthly"),
    repo: StockDataRepository = Depends(_get_repo),
):
    """Get historical K-line data."""
    # Build cache key
    cache_key = f"stock:daily:{code}:{start_date}:{end_date}:{period}"
    cached = redis_cache.get(cache_key)
    if cached:
        return {"data": cached}

    quotes = await repo.get_daily(code, start_date, end_date, period)

    items = []
    for q in quotes:
        items.append({
            "trade_date": q.trade_date.isoformat(),
            "open": float(q.open_price) if q.open_price else None,
            "high": float(q.high_price) if q.high_price else None,
            "low": float(q.low_price) if q.low_price else None,
            "close": float(q.close_price) if q.close_price else None,
            "volume": float(q.volume) if q.volume else None,
            "amount": float(q.amount) if q.amount else None,
            "pct_chg": float(q.pct_chg) if q.pct_chg else None,
            "data_source": q.data_source,
        })

    result = {
        "code": code,
        "period": period,
        "items": items,
    }

    # Cache for 24 hours
    redis_cache.set(cache_key, result, ttl=86400)

    return {"data": result}


@router.get("/{code}/financial")
async def get_stock_financial(
    code: str,
    repo: StockDataRepository = Depends(_get_repo),
):
    """Get financial data for a stock."""
    cached = redis_cache.get(f"stock:financial:{code}")
    if cached:
        return {"data": cached}

    financials = await repo.get_financial(code)

    items = []
    for f in financials:
        items.append({
            "report_date": f.report_date.isoformat(),
            "roe": float(f.roe) if f.roe else None,
            "net_profit": float(f.net_profit) if f.net_profit else None,
            "revenue": float(f.revenue) if f.revenue else None,
            "eps": float(f.eps) if f.eps else None,
            "gross_margin": float(f.gross_margin) if f.gross_margin else None,
            "debt_ratio": float(f.debt_ratio) if f.debt_ratio else None,
            "data_source": f.data_source,
        })

    result = {
        "code": code,
        "items": items,
    }

    # Cache for 24 hours
    redis_cache.set(f"stock:financial:{code}", result, ttl=86400)

    return {"data": result}


# ---------------------------------------------------------------------------
# 模块二新增接口
# ---------------------------------------------------------------------------

from app.infrastructure.repositories.mysql_stock_indicator_repo import MySQLStockIndicatorRepository
from app.infrastructure.repositories.mysql_article_stock_repo import MySQLArticleStockRepository
from app.application.use_cases.stock_detail import StockDetailUseCase
from app.application.use_cases.indicator_calc import IndicatorCalcUseCase


@router.get("/{code}/minute")
async def get_stock_minute(
    code: str,
    repo: StockDataRepository = Depends(_get_repo),
):
    """获取当日分时数据（从K线数据中按分钟粒度聚合，简化实现）。"""
    # 简化：返回最近交易日的分钟级别数据（实际需要数据源支持）
    # 当前实现：返回空列表，待接入实时分时数据源
    return {"data": {"code": code, "trade_date": date.today().isoformat(), "items": []}}


@router.get("/{code}/indicators")
async def get_stock_indicators(
    code: str,
    period: str = Query("daily", description="daily/weekly/monthly"),
    indicators: str = Query("ma,macd,kdj", description="逗号分隔的指标名"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """获取技术指标数据。"""
    cache_key = f"stock:indicators:{code}:{period}:{start_date}:{end_date}"
    cached = redis_cache.get(cache_key)
    if cached:
        return {"data": cached}

    indicator_repo = MySQLStockIndicatorRepository(db)
    stock_repo = MySQLStockDataRepository(db)
    uc = IndicatorCalcUseCase(stock_repo, indicator_repo)

    indicator_list = await uc.get_indicators(code, period, start_date, end_date)

    items = []
    for ind in indicator_list:
        item = {"trade_date": ind.trade_date.isoformat() if ind.trade_date else None}
        if "ma" in indicators:
            item.update({
                "ma5": float(ind.ma5) if ind.ma5 else None,
                "ma10": float(ind.ma10) if ind.ma10 else None,
                "ma20": float(ind.ma20) if ind.ma20 else None,
            })
        if "macd" in indicators:
            item.update({
                "macd_dif": float(ind.macd_dif) if ind.macd_dif else None,
                "macd_dea": float(ind.macd_dea) if ind.macd_dea else None,
                "macd_bar": float(ind.macd_bar) if ind.macd_bar else None,
            })
        if "kdj" in indicators:
            item.update({
                "kdj_k": float(ind.kdj_k) if ind.kdj_k else None,
                "kdj_d": float(ind.kdj_d) if ind.kdj_d else None,
                "kdj_j": float(ind.kdj_j) if ind.kdj_j else None,
            })
        items.append(item)

    result = {"code": code, "period": period, "items": items}
    redis_cache.set(cache_key, result, ttl=86400)
    return {"data": result}


@router.get("/{code}/detail")
async def get_stock_detail(
    code: str,
    db: AsyncSession = Depends(get_db),
):
    """获取个股详情聚合数据（基础信息+实时行情+最新财务）。"""
    cached = redis_cache.get(f"stock:detail:{code}")
    if cached:
        return {"data": cached}

    stock_repo = MySQLStockDataRepository(db)
    article_repo = MySQLArticleStockRepository(db)
    uc = StockDetailUseCase(stock_repo, article_repo)
    detail = await uc.get_detail(code)

    if not detail:
        raise HTTPException(status_code=404, detail=f"股票 {code} 不存在")

    result = {
        "stock_code": detail.stock_code,
        "name": detail.name,
        "exchange": detail.exchange,
        "industry": detail.industry,
        "industry_code": detail.industry_code,
        "total_market_cap": float(detail.total_market_cap) if detail.total_market_cap else None,
        "float_market_cap": float(detail.float_market_cap) if detail.float_market_cap else None,
        "list_date": detail.list_date.isoformat() if detail.list_date else None,
        "price": float(detail.price) if detail.price else None,
        "change_pct": float(detail.change_pct) if detail.change_pct else None,
        "change_amount": float(detail.change_amount) if detail.change_amount else None,
        "open_price": float(detail.open_price) if detail.open_price else None,
        "high_price": float(detail.high_price) if detail.high_price else None,
        "low_price": float(detail.low_price) if detail.low_price else None,
        "pre_close": float(detail.pre_close) if detail.pre_close else None,
        "volume": float(detail.volume) if detail.volume else None,
        "amount": float(detail.amount) if detail.amount else None,
        "pe_ttm": float(detail.pe_ttm) if detail.pe_ttm else None,
        "pb": float(detail.pb) if detail.pb else None,
        "quote_time": detail.quote_time.isoformat() if detail.quote_time else None,
        "report_date": detail.report_date.isoformat() if detail.report_date else None,
        "roe": float(detail.roe) if detail.roe else None,
        "net_profit": float(detail.net_profit) if detail.net_profit else None,
        "revenue": float(detail.revenue) if detail.revenue else None,
        "eps": float(detail.eps) if detail.eps else None,
        "gross_margin": float(detail.gross_margin) if detail.gross_margin else None,
        "debt_ratio": float(detail.debt_ratio) if detail.debt_ratio else None,
        "related_articles": detail.related_articles,
    }

    redis_cache.set(f"stock:detail:{code}", result, ttl=300)
    return {"data": result}


@router.get("/{code}/related-articles")
async def get_related_articles(
    code: str,
    limit: int = Query(50, description="最大返回数量"),
    db: AsyncSession = Depends(get_db),
):
    """获取与该股票相关的分析文章。"""
    cache_key = f"stock:related:{code}:{limit}"
    cached = redis_cache.get(cache_key)
    if cached:
        return {"data": cached}

    article_repo = MySQLArticleStockRepository(db)
    articles = await article_repo.get_by_stock(code, limit)

    items = []
    for a in articles:
        items.append({
            "article_id": a.article_id,
            "title": a.title or "",
            "summary": (a.summary or "")[:80],
            "saved_at": a.saved_at.isoformat() if a.saved_at else None,
        })

    result = {"code": code, "total": len(items), "items": items}
    redis_cache.set(cache_key, result, ttl=300)
    return {"data": result}
