"""ChanlunMonitorUseCase 单元测试（T027）。

验证：扫描范围解析、新鲜度跳过、并发异常隔离、run_log 生命周期。
"""

from dataclasses import replace
from datetime import date, datetime
from typing import Optional

import pytest

from app.application.use_cases.chanlun_calc import ChanlunCalcUseCase
from app.application.use_cases.chanlun_monitor import ChanlunMonitorUseCase
from app.domain.entities.chanlun import StructureSnapshot
from app.domain.entities.strategy import StrategyRunLog
from app.domain.entities.watchlist import WatchlistItem
from app.domain.models.stock_data import StockDailyQuote, StockKline30m

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

class FakeWatchlistRepo:
    def __init__(self, items):
        self._items = items
        self.called_with: Optional[str] = None

    async def get_all_items_by_user(self, user_id):
        self.called_with = user_id
        return self._items


class FakeChanlunCalc:
    """记录调用、可控异常。"""

    def __init__(self, fail_codes=None, algo_version="1.0.0"):
        self.calls: list[tuple[str, str]] = []
        self.fail_codes = set(fail_codes or [])
        self.algo_version = algo_version

    async def compute_and_persist(self, code, period):
        self.calls.append((code, period))
        if code in self.fail_codes:
            raise RuntimeError(f"boom {code}")
        return [], StructureSnapshot(stock_code=code, period=period), 0


class FakeChanlunRepo:
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


def _item(code):
    return WatchlistItem(group_id=1, stock_code=code)


# ---------------------------------------------------------------------------
# 测试
# ---------------------------------------------------------------------------

async def test_scan_all_success():
    wl = FakeWatchlistRepo([_item("600000"), _item("000001")])
    calc = FakeChanlunCalc()
    cr = FakeChanlunRepo()
    sd = FakeStockDataRepo(latest_daily=date(2026, 1, 10))
    mon = ChanlunMonitorUseCase(wl, calc, cr, sd, concurrency=5)

    log = await mon.scan("daily", user_id="u1")

    assert wl.called_with == "u1"
    assert log.status == "done"
    assert log.total == 2 and log.success == 2 and log.failed == 0
    assert len(calc.calls) == 2
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
    calc = FakeChanlunCalc()
    sd = FakeStockDataRepo(latest_daily=date(2026, 1, 10))
    mon = ChanlunMonitorUseCase(wl, calc, cr, sd, concurrency=5)

    log = await mon.scan("daily", user_id="u1")

    # stale → calc 未被调用；success=0；total 仍含该股
    assert calc.calls == []
    assert log.total == 1 and log.success == 0 and log.failed == 0


async def test_scan_failure_isolation():
    """单股异常计入 failed_detail，不阻断其余股票。"""
    wl = FakeWatchlistRepo([_item("600000"), _item("000001"), _item("000002")])
    calc = FakeChanlunCalc(fail_codes={"000001"})
    cr = FakeChanlunRepo()
    sd = FakeStockDataRepo(latest_daily=date(2026, 1, 10))
    mon = ChanlunMonitorUseCase(wl, calc, cr, sd, concurrency=3)

    log = await mon.scan("daily", user_id="u1")

    assert log.total == 3 and log.success == 2 and log.failed == 1
    assert cr.finished[0]["failed"] == 1
    detail = cr.finished[0]["failed_detail"]
    assert detail and detail[0]["stock_code"] == "000001"
    assert "boom" in detail[0]["reason"]


async def test_explicit_stock_codes_skip_watchlist():
    wl = FakeWatchlistRepo([_item("999999")])  # 不应被读取
    calc = FakeChanlunCalc()
    cr = FakeChanlunRepo()
    sd = FakeStockDataRepo(latest_daily=date(2026, 1, 10))
    mon = ChanlunMonitorUseCase(wl, calc, cr, sd, concurrency=5)

    log = await mon.scan("daily", user_id="u1", stock_codes=["600000", "600000", "000001"])

    assert wl.called_with is None            # 未查自选股
    assert log.total == 2                    # 去重
    assert {c for c, _ in calc.calls} == {"600000", "000001"}


async def test_m30_scan_uses_30m_freshness():
    snapshot = StructureSnapshot(
        stock_code="600000", period="m30",
        last_kline_time=datetime(2026, 1, 5, 11, 0),
    )
    cr = FakeChanlunRepo(structures={("600000", "m30"): snapshot})
    wl = FakeWatchlistRepo([_item("600000")])
    calc = FakeChanlunCalc()
    sd = FakeStockDataRepo(latest_m30=datetime(2026, 1, 5, 11, 0))  # 相同 → stale
    mon = ChanlunMonitorUseCase(wl, calc, cr, sd, concurrency=5)

    log = await mon.scan("m30", user_id="u1")

    assert calc.calls == []
    assert log.success == 0


async def test_progress_cb_invoked_per_stock():
    """每股完成调用一次 progress_cb，含 stock_code/period/status。"""
    wl = FakeWatchlistRepo([_item("600000"), _item("000001"), _item("000002")])
    calc = FakeChanlunCalc(fail_codes={"000002"})
    cr = FakeChanlunRepo()
    sd = FakeStockDataRepo(latest_daily=date(2026, 1, 10))
    msgs: list[dict] = []

    async def cb(m):
        msgs.append(m)

    mon = ChanlunMonitorUseCase(wl, calc, cr, sd, concurrency=5)
    await mon.scan("daily", user_id="u1", progress_cb=cb)

    assert len(msgs) == 3
    assert {m["stock_code"] for m in msgs} == {"600000", "000001", "000002"}
    status_by_code = {m["stock_code"]: m["status"] for m in msgs}
    assert status_by_code["600000"] == "success"
    assert status_by_code["000002"] == "failed"
    assert all(m["period"] == "daily" for m in msgs)
