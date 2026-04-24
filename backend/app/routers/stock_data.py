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


@router.get("/{code}")
async def get_stock_basic(
    code: str,
    repo: StockDataRepository = Depends(_get_repo),
):
    """Get stock basic information (highest priority source)."""
    # Check cache
    cached = await redis_cache.get(f"stock:basic:{code}")
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
    await redis_cache.set(f"stock:basic:{code}", result, ttl=86400)

    return {"data": result}


@router.get("/{code}/quote")
async def get_stock_quote(
    code: str,
    repo: StockDataRepository = Depends(_get_repo),
):
    """Get latest market quote for a stock."""
    # Check cache
    cached = await redis_cache.get(f"stock:quote:{code}")
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
    await redis_cache.set(f"stock:quote:{code}", result, ttl=300)

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
    cached = await redis_cache.get(cache_key)
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
    await redis_cache.set(cache_key, result, ttl=86400)

    return {"data": result}


@router.get("/{code}/financial")
async def get_stock_financial(
    code: str,
    repo: StockDataRepository = Depends(_get_repo),
):
    """Get financial data for a stock."""
    cached = await redis_cache.get(f"stock:financial:{code}")
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
    await redis_cache.set(f"stock:financial:{code}", result, ttl=86400)

    return {"data": result}
