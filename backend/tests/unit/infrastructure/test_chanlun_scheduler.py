"""缠论调度器单元测试（T028）。

``setup_scheduler`` 仅注册任务、不触发执行（任务函数内才用 ``session_factory``），
故无需真实 DB 即可断言任务注册与 cron 解析。
"""

from app.infrastructure.scheduler.chanlun_scheduler import _parse_cron, setup_scheduler


def test_parse_cron():
    assert _parse_cron("15:40") == (15, 40)
    assert _parse_cron("09:05") == (9, 5)


def test_setup_registers_jobs():
    sched = setup_scheduler(session_factory=lambda: None)
    assert sched is not None
    ids = {j.id for j in sched.get_jobs()}
    assert "chanlun_daily_scan" in ids
    assert "chanlun_m30_scan" in ids


def test_m30_trigger_covers_eight_points():
    """m30 触发器应在 8 个目标时点命中（用 9:30-15:00 外不命中做反向断言）。"""
    from datetime import datetime

    sched = setup_scheduler(session_factory=lambda: None)
    m30 = next(j for j in sched.get_jobs() if j.id == "chanlun_m30_scan")

    hits = {  # 周一各时点是否命中
        (10, 5): True, (10, 35): True, (11, 5): True, (11, 35): True,
        (13, 35): True, (14, 5): True, (14, 35): True, (15, 5): True,
        (13, 5): False,   # 午休不开仓后的那一根尚未收盘
        (12, 0): False,   # 午休
        (9, 35): False,   # 早盘尚未到 10:00 第一根
        (16, 0): False,   # 收盘后
    }
    for (h, m), expected in hits.items():
        # 周一（2026-08-10）
        fire_time = datetime(2026, 8, 10, h, m)
        triggered = m30.trigger.get_next_fire_time(None, fire_time)
        # 若该时点命中，下一次触发应就在该时点（同分钟）
        if expected:
            assert triggered is not None and triggered.hour == h and triggered.minute == m, (
                f"期望 {(h, m)} 命中，实际 {triggered}"
            )
        else:
            assert triggered is None or not (triggered.hour == h and triggered.minute == m), (
                f"期望 {(h, m)} 不命中，实际命中 {triggered}"
            )


# ---------------------------------------------------------------------------
# _pull_daily_quotes：日线定时扫描的数据前置拉取
# ---------------------------------------------------------------------------

import pytest
from unittest.mock import patch

pytestmark_pull = pytest.mark.asyncio


class _FakeSession:
    def __init__(self):
        self.committed = False
        self.rolled_back = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def commit(self):
        self.committed = True

    async def rollback(self):
        self.rolled_back = True


class _FakeRepo:
    instances = []

    def __init__(self, session):
        self.session = session
        self.upserted = []
        _FakeRepo.instances.append(self)

    async def upsert_daily_batch(self, quotes):
        self.upserted.append(quotes)


@pytest.mark.asyncio
async def test_pull_daily_quotes_upserts_and_clears_cache():
    """正常路径：拉取 → 清洗 → upsert → 清缓存 → commit。"""
    _FakeRepo.instances = []
    sessions = []

    def factory():
        s = _FakeSession()
        sessions.append(s)
        return s

    raw = [{"code": "600000", "trade_date": "2026-08-14", "close": "10.0"}]

    class _FakeSina:
        def fetch_daily_quote(self, code, start_date, end_date, period="daily"):
            return raw

    cleared = []

    async def fake_clear(code, period):
        cleared.append((code, period))

    with patch("app.application.sync.sina_sync_client.SinaSyncClient", _FakeSina), \
         patch("app.domain.services.data_cleaner.clean_daily_quote", side_effect=lambda r, s: r), \
         patch(
             "app.infrastructure.repositories.mysql_stock_data_repo.MySQLStockDataRepository",
             _FakeRepo,
         ), \
         patch("app.application.sync.sync_executor._clear_kline_cache", fake_clear):
        from app.infrastructure.scheduler.chanlun_scheduler import _pull_daily_quotes
        await _pull_daily_quotes(factory, ["600000", "000001"])

    assert len(_FakeRepo.instances) == 2
    assert all(inst.upserted == [raw] for inst in _FakeRepo.instances)
    assert set(cleared) == {("600000", "daily"), ("000001", "daily")}
    assert len(sessions) == 2 and all(s.committed for s in sessions)


@pytest.mark.asyncio
async def test_pull_daily_quotes_single_failure_not_blocking():
    """单股网络异常 → 记 warning，不影响其他股；落库异常走 rollback。"""
    _FakeRepo.instances = []
    sessions = []

    def factory():
        s = _FakeSession()
        sessions.append(s)
        return s

    class _FakeSina:
        def fetch_daily_quote(self, code, start_date, end_date, period="daily"):
            if code == "BAD001":
                raise RuntimeError("network down")
            return [{"code": code, "trade_date": "2026-08-14"}]

    class _FailingRepo:
        def __init__(self, session):
            self.session = session

        async def upsert_daily_batch(self, quotes):
            raise RuntimeError("db error")

    with patch("app.application.sync.sina_sync_client.SinaSyncClient", _FakeSina), \
         patch("app.domain.services.data_cleaner.clean_daily_quote", side_effect=lambda r, s: r), \
         patch(
             "app.infrastructure.repositories.mysql_stock_data_repo.MySQLStockDataRepository",
             _FailingRepo,
         ), \
         patch("app.application.sync.sync_executor._clear_kline_cache"):
        from app.infrastructure.scheduler.chanlun_scheduler import _pull_daily_quotes
        await _pull_daily_quotes(factory, ["BAD001", "600000"])  # 不抛

    # BAD001 网络异常在 gather 结果里被记日志；600000 落库失败 rollback
    assert sessions[0].rolled_back is True


@pytest.mark.asyncio
async def test_pull_daily_quotes_dirty_rows_skipped():
    """清洗失败的脏数据跳过；全部脏 → 不开 session 落库。"""
    _FakeRepo.instances = []
    sessions = []

    def factory():
        s = _FakeSession()
        sessions.append(s)
        return s

    class _FakeSina:
        def fetch_daily_quote(self, code, start_date, end_date, period="daily"):
            return [{"bad": "row"}]

    def dirty_cleaner(r, s):
        raise ValueError("dirty")

    with patch("app.application.sync.sina_sync_client.SinaSyncClient", _FakeSina), \
         patch("app.domain.services.data_cleaner.clean_daily_quote", dirty_cleaner), \
         patch(
             "app.infrastructure.repositories.mysql_stock_data_repo.MySQLStockDataRepository",
             _FakeRepo,
         ), \
         patch("app.application.sync.sync_executor._clear_kline_cache"):
        from app.infrastructure.scheduler.chanlun_scheduler import _pull_daily_quotes
        await _pull_daily_quotes(factory, ["600000"])

    assert sessions == []      # 无净数据 → 未开 session
    assert _FakeRepo.instances == []
