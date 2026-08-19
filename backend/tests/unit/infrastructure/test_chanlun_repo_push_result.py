"""缠论 Repository 推送结果回写 + upsert id 回填测试（内存 SQLite）。

``MySQLChanlunRepository`` 的 SQL 对象在 SQLite 上同样可执行（本次涉及的
``update ... in_`` 无 MySQL 方言依赖），用 aiosqlite 内存库真实跑一遍：
1. ``upsert_signals_batch`` flush 后把自增 id 回填到实体（推送回写的前提）；
2. ``update_push_result`` 按 id 批量落 push_status / push_message_id / push_time。
"""

from datetime import datetime
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.domain.entities.chanlun import ChanlunSignal
from app.infrastructure.db.models import StrategySignalModel
from app.infrastructure.repositories.mysql_chanlun_repo import MySQLChanlunRepository

pytestmark = pytest.mark.asyncio


def _sig(**kw) -> ChanlunSignal:
    base = dict(
        stock_code="600519",
        period="m30",
        signal_type="buy3",
        structure_level="stroke",
        signal_time=datetime(2026, 8, 18, 14, 0),
        trigger_price=Decimal("428.960"),
        algo_version="1.0.0",
    )
    base.update(kw)
    return ChanlunSignal(**base)


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        # 只建本次涉及的表（全量 metadata 含 MEDIUMTEXT 等 MySQL 方言列，SQLite 建不了）
        await conn.run_sync(StrategySignalModel.__table__.create)
    maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as s:
        yield s
    await engine.dispose()


async def test_upsert_backfills_autoincrement_id(session):
    repo = MySQLChanlunRepository(session)
    inserted = await repo.upsert_signals_batch([_sig(), _sig(stock_code="000858")])
    await session.commit()

    assert len(inserted) == 2
    assert all(s.id is not None for s in inserted)  # id 已回填，推送回写可定位行
    assert inserted[0].id != inserted[1].id


async def test_upsert_dedup_not_counted_as_new(session):
    repo = MySQLChanlunRepository(session)
    first = await repo.upsert_signals_batch([_sig()])
    await session.commit()
    again = await repo.upsert_signals_batch([_sig()])  # 同 dedup_key 二次写入
    await session.commit()

    assert len(first) == 1
    assert again == []  # 已存在不计新增（推送不会重复触发）
    assert first[0].id is not None


async def test_update_push_result_persists_fields(session):
    repo = MySQLChanlunRepository(session)
    inserted = await repo.upsert_signals_batch([_sig(), _sig(stock_code="000858")])
    await session.commit()
    ids = [s.id for s in inserted]

    rows = await repo.update_push_result(ids, "success", "MSG-XYZ")
    await session.commit()

    assert rows == 2
    result = await session.execute(
        StrategySignalModel.__table__.select().where(StrategySignalModel.id.in_(ids))
    )
    for row in result.fetchall():
        assert row.push_status == "success"
        assert row.push_message_id == "MSG-XYZ"
        assert row.push_time is not None


async def test_update_push_result_empty_ids_noop(session):
    repo = MySQLChanlunRepository(session)
    assert await repo.update_push_result([], "failed") == 0


async def test_update_push_result_empty_message_id_stores_null(session):
    repo = MySQLChanlunRepository(session)
    inserted = await repo.upsert_signals_batch([_sig()])
    await session.commit()

    await repo.update_push_result([inserted[0].id], "failed", "")
    await session.commit()

    result = await session.execute(
        StrategySignalModel.__table__.select().where(
            StrategySignalModel.id == inserted[0].id
        )
    )
    row = result.fetchone()
    assert row.push_status == "failed"
    assert row.push_message_id is None  # 空串归一为 NULL
