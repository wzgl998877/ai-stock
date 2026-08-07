"""ChanlunMonitorUseCase 单元测试（T027）。

验证：扫描范围解析、新鲜度跳过、并发异常隔离、run_log 生命周期，以及
**每股独立 session** 的并发契约（``AsyncSession`` 非并发安全，gather 并发下不可共享）。
"""

from dataclasses import replace
from datetime import date, datetime
from typing import Optional

import pytest

from app.application.use_cases.chanlun_monitor import ChanlunMonitorUseCase
from app.domain.entities.chanlun import StructureSnapshot
from app.domain.entities.strategy import StrategyRunLog
from app.domain.entities.watchlist import WatchlistItem
from app.domain.models.stock_data import StockDailyQuote

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

class FakeSession:
    """带唯一 id 的假 session；记录 commit/rollback，支持 ``async with``。"""

    _next_id = 0

    def __init__(self):
        type(self)._next_id += 1
        self.id = type(self)._next_id
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


class FakeWatchlistRepo:
    def __init__(self, items):
        self._items = items
        self.called_with: Optional[str] = None

    async def get_all_items_by_user(self, user_id):
        self.called_with = user_id
        return self._items


class FakeChanlunRepo:
    """主流程（run_log/配置）+ 每股（get_structure）共用。"""

    def __init__(self, structures=None):
        self.created: list[StrategyRunLog] = []
        self.finished: list[dict] = []
        self.structures = structures or {}
        self._next_id = 1

    async def create_run_log(self, log):
        log = replace(log, id=self._next_id)
        self._next_id += 1
        self.created.append(log)
        return log

    async def finish_run_log(self, log_id, status, success, failed, failed_detail=None, duration_ms=None):
        self.finished.append({
            "log_id": log_id, "status": status, "success": success, "failed": failed,
            "failed_detail": failed_detail, "duration_ms": duration_ms,
        })

    async def get_structure(self, code, period):
        return self.structures.get((code, period))

    async def get_monitor_configs(self, user_id):
        return []  # 不过滤


class FakeStockDataRepo:
    def __init__(self, latest_daily=None, latest_m30=None):
        self.latest_daily = latest_daily  # date
        self.latest_m30 = latest_m30      # datetime

    async def get_daily(self, code, start_date=None, end_date=None, period="daily"):
        if self.latest_daily is None:
            return []
        return [StockDailyQuote(code=code, trade_date=self.latest_daily, period="daily", close_price=10)]

    async def get_latest_kline_30m_time(self, code):
        return self.latest_m30


class FakeCalc:
    """每股 ``build_calc`` 产出；``chanlun_repo``/``stock_data_repo`` 指向共享 fake。"""

    def __init__(self, session, chanlun_repo, stock_data_repo, fail_codes=(), calls=None):
        self.session = session
        self.chanlun_repo = chanlun_repo
        self.stock_data_repo = stock_data_repo
        self._fail_codes = set(fail_codes or [])
        self._calls = calls if calls is not None else []

    async def compute_and_persist(self, code, period):
        self._calls.append((code, period))
        if code in self._fail_codes:
            raise RuntimeError(f"boom {code}")
        return [], StructureSnapshot(stock_code=code, period=period), 0


def _item(code):
    return WatchlistItem(group_id=1, stock_code=code)


def _make_monitor(wl, cr, sd, fail_codes=(), concurrency=5):
    """用新签名装配 monitor：session_factory 每次返回新 FakeSession 并收集。"""
    sessions: list[FakeSession] = []
    calc_calls: list[tuple[str, str]] = []

    def session_factory():
        s = FakeSession()
        sessions.append(s)
        return s

    def build_calc(s):
        return FakeCalc(s, chanlun_repo=cr, stock_data_repo=sd,
                        fail_codes=fail_codes, calls=calc_calls)

    mon = ChanlunMonitorUseCase(
        watchlist_repo=wl,
        chanlun_repo=cr,
        algo_version="1.0.0",
        session_factory=session_factory,
        build_calc=build_calc,
        concurrency=concurrency,
    )
    return mon, sessions, calc_calls


# ---------------------------------------------------------------------------
# 测试
# ---------------------------------------------------------------------------

async def test_scan_all_success():
    wl = FakeWatchlistRepo([_item("600000"), _item("000001")])
    cr = FakeChanlunRepo()
    sd = FakeStockDataRepo(latest_daily=date(2026, 1, 10))
    mon, _sessions, calc_calls = _make_monitor(wl, cr, sd)

    log = await mon.scan("daily", user_id="u1")

    assert wl.called_with == "u1"
    assert log.status == "done"
    assert log.total == 2 and log.success == 2 and log.failed == 0
    assert len(calc_calls) == 2
    assert len(cr.created) == 1 and cr.created[0].status == "running"
    assert len(cr.finished) == 1
    assert cr.finished[0]["status"] == "done" and cr.finished[0]["success"] == 2
    assert cr.finished[0]["failed_detail"] is None


async def test_scan_stale_skipped():
    """快照 last_kline_time == 当前最新 → no_new_data 跳过，不调 calc。"""
    snapshot = StructureSnapshot(
        stock_code="600000", period="daily",
        last_kline_time=datetime(2026, 1, 10),  # 与库中最新相同
    )
    cr = FakeChanlunRepo(structures={("600000", "daily"): snapshot})
    wl = FakeWatchlistRepo([_item("600000")])
    sd = FakeStockDataRepo(latest_daily=date(2026, 1, 10))
    mon, _sessions, calc_calls = _make_monitor(wl, cr, sd)

    log = await mon.scan("daily", user_id="u1")

    # stale → calc 未被调用；success=0；total 仍含该股
    assert calc_calls == []
    assert log.total == 1 and log.success == 0 and log.failed == 0


async def test_scan_failure_isolation():
    """单股异常计入 failed_detail，不阻断其余股票；失败股 rollback。"""
    wl = FakeWatchlistRepo([_item("600000"), _item("000001"), _item("000002")])
    cr = FakeChanlunRepo()
    sd = FakeStockDataRepo(latest_daily=date(2026, 1, 10))
    mon, sessions, _calc_calls = _make_monitor(wl, cr, sd, fail_codes={"000001"})

    log = await mon.scan("daily", user_id="u1")

    assert log.total == 3 and log.success == 2 and log.failed == 1
    assert cr.finished[0]["failed"] == 1
    detail = cr.finished[0]["failed_detail"]
    assert detail and detail[0]["stock_code"] == "000001"
    assert "boom" in detail[0]["reason"]
    # 失败股 rollback、未 commit
    assert [s for s in sessions if s.rolled_back]  # 有一股 rollback


async def test_explicit_stock_codes_skip_watchlist():
    wl = FakeWatchlistRepo([_item("999999")])  # 不应被读取
    cr = FakeChanlunRepo()
    sd = FakeStockDataRepo(latest_daily=date(2026, 1, 10))
    mon, _sessions, calc_calls = _make_monitor(wl, cr, sd)

    log = await mon.scan("daily", user_id="u1", stock_codes=["600000", "600000", "000001"])

    assert wl.called_with is None            # 未查自选股
    assert log.total == 2                    # 去重
    assert {c for c, _ in calc_calls} == {"600000", "000001"}


async def test_m30_scan_uses_30m_freshness():
    snapshot = StructureSnapshot(
        stock_code="600000", period="m30",
        last_kline_time=datetime(2026, 1, 5, 11, 0),
    )
    cr = FakeChanlunRepo(structures={("600000", "m30"): snapshot})
    wl = FakeWatchlistRepo([_item("600000")])
    sd = FakeStockDataRepo(latest_m30=datetime(2026, 1, 5, 11, 0))  # 相同 → stale
    mon, _sessions, calc_calls = _make_monitor(wl, cr, sd)

    log = await mon.scan("m30", user_id="u1")

    assert calc_calls == []
    assert log.success == 0


async def test_progress_cb_invoked_per_stock():
    """每股完成调用一次 progress_cb，含 stock_code/period/status。"""
    wl = FakeWatchlistRepo([_item("600000"), _item("000001"), _item("000002")])
    cr = FakeChanlunRepo()
    sd = FakeStockDataRepo(latest_daily=date(2026, 1, 10))
    mon, _sessions, _calc_calls = _make_monitor(wl, cr, sd, fail_codes={"000002"})
    msgs: list[dict] = []

    async def cb(m):
        msgs.append(m)

    await mon.scan("daily", user_id="u1", progress_cb=cb)

    assert len(msgs) == 3
    assert {m["stock_code"] for m in msgs} == {"600000", "000001", "000002"}
    status_by_code = {m["stock_code"]: m["status"] for m in msgs}
    assert status_by_code["600000"] == "success"
    assert status_by_code["000002"] == "failed"
    assert all(m["period"] == "daily" for m in msgs)


async def test_each_stock_uses_independent_session():
    """并发扫描 N 股 → 每股一个互异 session（AsyncSession 非共享主 session）。

    这是 ``Session is already flushing`` 修复的核心契约。
    """
    wl = FakeWatchlistRepo([_item("000001"), _item("000002"), _item("000003")])
    cr = FakeChanlunRepo()
    sd = FakeStockDataRepo(latest_daily=date(2026, 1, 10))
    mon, sessions, _calc_calls = _make_monitor(wl, cr, sd, concurrency=5)

    await mon.scan("daily", user_id="u1")

    assert len(sessions) == 3                          # 每股一个 session
    assert len({s.id for s in sessions}) == 3          # id 互异（非同一共享 session）
    assert all(s.committed for s in sessions)          # 全部成功 → 全 commit
