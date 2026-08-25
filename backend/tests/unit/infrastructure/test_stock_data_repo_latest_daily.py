"""MySQLStockDataRepository.get_latest_daily_date 测试（内存 SQLite）。

日线增量拉取（2026-08-25 新浪 456 封禁后改造）的缺口判断依据：
无数据返回 None；多数据源/多日期时取最新；``source`` 过滤生效。
"""

from datetime import date
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.infrastructure.db.models import StockDailyQuoteModel
from app.infrastructure.repositories.mysql_stock_data_repo import (
    MySQLStockDataRepository,
)

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(StockDailyQuoteModel.__table__.create)
    maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as s:
        yield s
    await engine.dispose()


def _row(code: str, d: date, source: str = "sina") -> StockDailyQuoteModel:
    return StockDailyQuoteModel(
        code=code, trade_date=d, period="daily",
        open_price=Decimal("1"), high_price=Decimal("1"),
        low_price=Decimal("1"), close_price=Decimal("1"),
        data_source=source,
    )


async def test_returns_none_when_no_data(session):
    repo = MySQLStockDataRepository(session)
    assert await repo.get_latest_daily_date("600000") is None


async def test_returns_latest_date(session):
    repo = MySQLStockDataRepository(session)
    session.add_all([
        _row("600000", date(2026, 8, 20)),
        _row("600000", date(2026, 8, 22)),
        _row("600000", date(2026, 8, 21)),
    ])
    await session.flush()

    assert await repo.get_latest_daily_date("600000") == date(2026, 8, 22)


async def test_source_filter(session):
    repo = MySQLStockDataRepository(session)
    session.add_all([
        _row("600000", date(2026, 8, 22), source="sina"),
        _row("600000", date(2026, 8, 24), source="akshare"),
    ])
    await session.flush()

    # 不过滤：全部数据源里最新
    assert await repo.get_latest_daily_date("600000") == date(2026, 8, 24)
    # 过滤 sina：只看 sina 行（增量落库按 source 幂等，判断口径须一致）
    assert await repo.get_latest_daily_date("600000", source="sina") == date(2026, 8, 22)
    # 过滤不存在的源
    assert await repo.get_latest_daily_date("600000", source="tencent") is None
