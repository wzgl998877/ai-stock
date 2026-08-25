"""日 K「一天一条」语义测试（n8o9p0q1r2s3，内存 SQLite）。

- ``upsert_daily_batch``：同步即全源覆盖——不同源后写的覆盖先写的（按日期）；
- ``get_daily``：直读全部行，不再按数据源优先级挑选。
"""

from datetime import date
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.domain.models.stock_data import StockDailyQuote
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


def _q(code: str, d: date, source: str, close: str = "10.0") -> StockDailyQuote:
    return StockDailyQuote(
        code=code, trade_date=d, period="daily",
        open_price=Decimal(close), high_price=Decimal(close),
        low_price=Decimal(close), close_price=Decimal(close),
        data_source=source,
    )


async def test_upsert_overwrites_across_sources(session):
    """后到的源覆盖同日旧数据（同步即全源覆盖）。"""
    repo = MySQLStockDataRepository(session)
    await repo.upsert_daily_batch([_q("600000", date(2026, 8, 24), "tushare", "9.9")])
    await session.flush()
    # 换源重写同一天：应替换而非并存
    await repo.upsert_daily_batch([_q("600000", date(2026, 8, 24), "sina", "10.5")])
    await session.flush()

    quotes = await repo.get_daily("600000")
    assert len(quotes) == 1                      # 一天一条
    assert quotes[0].data_source == "sina"       # 后写的赢
    assert quotes[0].close_price == Decimal("10.5")


async def test_upsert_partial_overlap_replaces_only_batched_dates(session):
    """批量覆盖只影响本批日期，未覆盖日期保留。"""
    repo = MySQLStockDataRepository(session)
    await repo.upsert_daily_batch([
        _q("600000", date(2026, 8, 22), "sina", "9.0"),
        _q("600000", date(2026, 8, 25), "sina", "10.0"),
    ])
    await session.flush()
    await repo.upsert_daily_batch([_q("600000", date(2026, 8, 25), "sina", "11.0")])
    await session.flush()

    quotes = await repo.get_daily("600000")
    assert [(q.trade_date, q.close_price) for q in quotes] == [
        (date(2026, 8, 22), Decimal("9.0")),   # 未覆盖日期保留
        (date(2026, 8, 25), Decimal("11.0")),  # 覆盖日更新
    ]


async def test_get_daily_returns_all_rows_no_priority(session):
    """get_daily 直读：不同日期来自不同源时全部返回（升序）。"""
    repo = MySQLStockDataRepository(session)
    # 模拟 migration 去重后的典型形态：不同日期段不同源
    await repo.upsert_daily_batch([
        _q("000707", date(2024, 12, 30), "tushare"),
        _q("000707", date(2024, 12, 31), "tushare"),
    ])
    await session.flush()
    await repo.upsert_daily_batch([_q("000707", date(2026, 8, 25), "sina", "12.0")])
    await session.flush()

    quotes = await repo.get_daily("000707")
    # 修复前 bug：优先级挑源只返回 tushare 段，sina 新数据永远不可见
    assert len(quotes) == 3
    assert [q.data_source for q in quotes] == ["tushare", "tushare", "sina"]
    assert quotes[-1].trade_date == date(2026, 8, 25)
