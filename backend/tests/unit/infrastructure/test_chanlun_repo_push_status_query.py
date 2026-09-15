"""``get_signals_by_push_status`` 补推候选查询测试（内存 SQLite）。

对标 ``test_chanlun_repo_push_result.py``：SQL 对象在 SQLite 上同样可执行
（本次涉及的 ``in_`` / ``>=`` 无 MySQL 方言依赖），用 aiosqlite 真实跑一遍。

补推候选 = 近期 ``push_status`` 为 failed / skipped 的信号：
failed=推送尝试失败；skipped=推送时无 context_token。两者都是「未送达、可重试」。
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

FROM = datetime(2026, 9, 1)
RECENT = datetime(2026, 9, 14, 15, 0)
OLD = datetime(2026, 8, 1, 15, 0)


def _sig(**kw) -> ChanlunSignal:
    base = dict(
        stock_code="600519",
        period="daily",
        signal_type="buy3",
        structure_level="stroke",
        signal_time=RECENT,
        trigger_price=Decimal("428.960"),
        algo_version="1.1.0",
    )
    base.update(kw)
    return ChanlunSignal(**base)


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(StrategySignalModel.__table__.create)
    maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as s:
        yield s
    await engine.dispose()


async def _seed(repo, session, specs: list[tuple[str, object]]) -> dict:
    """按 [(状态, 信号覆盖项)] 建行；状态 None 表示不回写（push_status 保持 NULL）。"""
    signals = await repo.upsert_signals_batch([s for _, s in specs])
    await session.commit()
    for sig, (status, _) in zip(signals, specs):
        if status is not None:
            await repo.update_push_result([sig.id], status)
    await session.commit()
    return {s.stock_code: s for s in signals}


async def test_returns_only_retryable_statuses(session):
    """只取 failed / skipped；success 与 NULL（未尝试）被排除。"""
    repo = MySQLChanlunRepository(session)
    await _seed(repo, session, [
        ("success", _sig(stock_code="A")),
        ("failed", _sig(stock_code="B")),
        ("skipped", _sig(stock_code="C")),
        (None, _sig(stock_code="D")),          # 从未尝试
    ])

    got = await repo.get_signals_by_push_status(["failed", "skipped"], FROM)

    assert sorted(s.stock_code for s in got) == ["B", "C"]


async def test_signal_time_window_excludes_old(session):
    """回看窗口生效：窗口外的陈旧信号不再作为候选（自动退出重试）。"""
    repo = MySQLChanlunRepository(session)
    await _seed(repo, session, [
        ("failed", _sig(stock_code="RECENT", signal_time=RECENT)),
        ("failed", _sig(stock_code="OLD", signal_time=OLD)),
    ])

    got = await repo.get_signals_by_push_status(["failed"], FROM)

    assert [s.stock_code for s in got] == ["RECENT"]


async def test_period_and_version_filters(session):
    """period / algo_version 为 None 时不限（补推跨周期跨版本）。"""
    repo = MySQLChanlunRepository(session)
    await _seed(repo, session, [
        ("failed", _sig(stock_code="D_V2", period="daily", algo_version="1.1.0")),
        ("failed", _sig(stock_code="D_V1", period="daily", algo_version="1.0.0")),
        ("failed", _sig(stock_code="M_V2", period="m30", algo_version="1.1.0")),
    ])

    all_rows = await repo.get_signals_by_push_status(["failed"], FROM)
    assert len(all_rows) == 3

    daily_only = await repo.get_signals_by_push_status(["failed"], FROM, period="daily")
    assert sorted(s.stock_code for s in daily_only) == ["D_V1", "D_V2"]

    both = await repo.get_signals_by_push_status(
        ["failed"], FROM, period="daily", algo_version="1.1.0"
    )
    assert [s.stock_code for s in both] == ["D_V2"]


async def test_limit_keeps_newest_first(session):
    """按 signal_time 倒序取前 limit 条：优先补推最新信号（市场相关度最高）。"""
    repo = MySQLChanlunRepository(session)
    await _seed(repo, session, [
        ("failed", _sig(stock_code="T1", signal_time=datetime(2026, 9, 10, 15, 0))),
        ("failed", _sig(stock_code="T2", signal_time=datetime(2026, 9, 12, 15, 0))),
        ("failed", _sig(stock_code="T3", signal_time=datetime(2026, 9, 14, 15, 0))),
    ])

    got = await repo.get_signals_by_push_status(["failed"], FROM, limit=2)

    assert [s.stock_code for s in got] == ["T3", "T2"]


async def test_empty_statuses_returns_empty(session):
    """空入参短路：避免生成 ``IN ()`` 这种非法 SQL。"""
    repo = MySQLChanlunRepository(session)
    await _seed(repo, session, [("failed", _sig(stock_code="A"))])

    assert await repo.get_signals_by_push_status([], FROM) == []


async def test_no_candidates_returns_empty(session):
    repo = MySQLChanlunRepository(session)
    await _seed(repo, session, [("success", _sig(stock_code="A"))])

    assert await repo.get_signals_by_push_status(["failed", "skipped"], FROM) == []
