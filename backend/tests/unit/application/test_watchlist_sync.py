"""自选股按分组批量同步测试。

覆盖：
- ``WatchlistSyncUseCase.collect_unique_codes``：跨分组去重、空 stock_code 过滤；
- ``watchlist_batch_sync._sync_one_stock``：日K落库+清缓存、30m 被调、异常 rollback 抛出；
- ``watchlist_batch_sync.launch_batch_sync``：全成功/部分失败均 completed、单股失败不阻断；
- router ``POST /api/v1/watchlist/sync``：参数校验、单飞锁 409、正常返回。

数据源（新浪）、Redis、真实 DB 均通过 monkeypatch/mock 隔离，不发起真实网络/IO。
"""

from typing import List

import httpx
import pytest
from fastapi import FastAPI

from app.application.sync import watchlist_batch_sync
from app.application.sync.sync_executor import _get_lock
from app.application.use_cases.watchlist_sync import WatchlistSyncUseCase
from app.domain.entities.watchlist import WatchlistItem
from app.routers import watchlist as wl_router

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# 测试辅助：Fake watchlist repo
# ---------------------------------------------------------------------------


class _FakeWatchlistRepo:
    """模拟 WatchlistRepository，仅实现 get_items。"""

    def __init__(self, items_by_group: dict[int, List[WatchlistItem]]):
        self._items = items_by_group

    async def get_items(self, group_id: int) -> List[WatchlistItem]:
        return list(self._items.get(group_id, []))


def _item(code: str) -> WatchlistItem:
    return WatchlistItem(group_id=0, stock_code=code, stock_name=f"name_{code}")


# ---------------------------------------------------------------------------
# WatchlistSyncUseCase.collect_unique_codes
# ---------------------------------------------------------------------------


async def test_collect_unique_codes_dedup_across_groups():
    repo = _FakeWatchlistRepo({
        1: [_item("600519"), _item("000001")],
        2: [_item("000001"), _item("002594")],  # 000001 跨组重复
    })
    uc = WatchlistSyncUseCase(repo)

    codes = await uc.collect_unique_codes("u1", [1, 2])

    assert codes == ["000001", "002594", "600519"]  # 去重 + 升序


async def test_collect_unique_codes_filters_empty_code():
    dirty = WatchlistItem(group_id=0, stock_code="", stock_name="empty")
    repo = _FakeWatchlistRepo({1: [_item("600519"), dirty]})
    uc = WatchlistSyncUseCase(repo)

    codes = await uc.collect_unique_codes("u1", [1])

    assert codes == ["600519"]


async def test_collect_unique_codes_empty_when_no_groups():
    repo = _FakeWatchlistRepo({1: [], 2: []})
    uc = WatchlistSyncUseCase(repo)

    assert await uc.collect_unique_codes("u1", [1, 2]) == []
    assert await uc.collect_unique_codes("u1", []) == []


# ---------------------------------------------------------------------------
# _sync_one_stock
# ---------------------------------------------------------------------------


class _FakeStockRepo:
    def __init__(self):
        self.daily_upserted: list = []

    async def upsert_daily_batch(self, quotes):
        self.daily_upserted.extend(quotes)


class _FakeSession:
    """模拟独立 session（async with 上下文）。记录 commit/rollback。"""

    def __init__(self):
        self.committed = False
        self.rolled_back = False

    async def commit(self):
        self.committed = True

    async def rollback(self):
        self.rolled_back = True

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


def _make_session_factory():
    sessions: list[_FakeSession] = []

    def _factory():
        s = _FakeSession()
        sessions.append(s)
        return s

    return _factory, sessions


@pytest.fixture
def patched_dependencies(monkeypatch):
    """统一 mock 数据源、仓库、缓存清除、30m 同步，返回断言用的 dict。"""
    captured: dict = {
        "daily_raw": None,
        "clear_cache_calls": [],
        "sync_30m_calls": [],
        "stock_repo_calls": 0,
    }

    # mock SinaSyncClient.fetch_daily_quote（同步函数，被 asyncio.to_thread 包装）
    def _fake_fetch(self, code, start_date, end_date, period="daily"):
        captured["daily_raw"] = (code, start_date, end_date, period)
        return [
            {"code": code, "trade_date": "2026-08-05", "open": 10, "high": 11,
             "low": 9, "close": 10.5, "volume": 1000, "amount": 10000, "period": "daily"},
        ]

    monkeypatch.setattr(
        watchlist_batch_sync.SinaSyncClient, "fetch_daily_quote", _fake_fetch
    )

    fake_repo = _FakeStockRepo()

    # _sync_one_stock 内部 `from ... import MySQLStockDataRepository` 取的是源模块的类，
    # 所以 patch 源模块属性才能生效。
    import app.infrastructure.repositories.mysql_stock_data_repo as stock_repo_mod
    monkeypatch.setattr(stock_repo_mod, "MySQLStockDataRepository", lambda session: fake_repo)

    # mock _clear_kline_cache（sync_executor 模块）
    import app.application.sync.sync_executor as sync_executor_mod

    async def _fake_clear(code, period):
        captured["clear_cache_calls"].append((code, period))

    monkeypatch.setattr(sync_executor_mod, "_clear_kline_cache", _fake_clear)

    # mock sync_stock_30m（避免真实拉取）
    async def _fake_sync_30m(code, repo):
        captured["sync_30m_calls"].append(code)

    monkeypatch.setattr(watchlist_batch_sync, "sync_stock_30m", _fake_sync_30m)

    captured["fake_repo"] = fake_repo
    return captured


async def test_sync_one_stock_daily_and_30m_called(patched_dependencies):
    factory, sessions = _make_session_factory()

    await watchlist_batch_sync._sync_one_stock(
        "600519", factory, "2025-08-12", "2026-08-12"
    )

    # 日K落库
    assert len(patched_dependencies["fake_repo"].daily_upserted) == 1
    # 日K缓存清除
    assert ("600519", "daily") in patched_dependencies["clear_cache_calls"]
    # 30m 被调
    assert patched_dependencies["sync_30m_calls"] == ["600519"]
    # commit 成功
    assert sessions and sessions[0].committed is True
    assert sessions[0].rolled_back is False


async def test_sync_one_stock_rolls_back_on_failure(monkeypatch, patched_dependencies):
    # 让 sync_stock_30m 抛异常，验证 rollback 且异常向上抛
    async def _boom(code, repo):
        raise RuntimeError("30m boom")

    monkeypatch.setattr(watchlist_batch_sync, "sync_stock_30m", _boom)

    factory, sessions = _make_session_factory()

    with pytest.raises(RuntimeError, match="30m boom"):
        await watchlist_batch_sync._sync_one_stock(
            "600519", factory, "2025-08-12", "2026-08-12"
        )

    assert sessions[0].rolled_back is True


# ---------------------------------------------------------------------------
# launch_batch_sync
# ---------------------------------------------------------------------------


async def test_launch_batch_sync_all_success(monkeypatch):
    calls: list[str] = []
    updates: list[tuple] = []

    async def _fake_one(code, factory, start_date, end_date):
        calls.append(code)

    monkeypatch.setattr(watchlist_batch_sync, "_sync_one_stock", _fake_one)

    async def _update_cb(task_id, status, success=0, fail=0, processed=0, error=None):
        updates.append((status, success, fail, processed, error))

    bg = watchlist_batch_sync.launch_batch_sync(
        "tid-1", ["600519", "000001", "002594"], None, _update_cb
    )
    await bg

    # 所有股票都被拉取
    assert sorted(calls) == ["000001", "002594", "600519"]
    # 状态：running → completed
    assert updates[0][0] == "running"
    assert updates[-1] == ("completed", 3, 0, 3, None)


async def test_launch_batch_sync_partial_failure_still_completed(monkeypatch):
    updates: list[tuple] = []

    async def _flaky(code, factory, start_date, end_date):
        if code == "000001":
            raise ValueError("fail this one")

    monkeypatch.setattr(watchlist_batch_sync, "_sync_one_stock", _flaky)

    async def _update_cb(task_id, status, success=0, fail=0, processed=0, error=None):
        updates.append((status, success, fail, processed, error))

    bg = watchlist_batch_sync.launch_batch_sync(
        "tid-2", ["600519", "000001", "002594"], None, _update_cb
    )
    await bg  # 单股失败不应让 gather 抛异常

    assert updates[-1] == ("completed", 2, 1, 3, None)


async def test_launch_batch_sync_update_cb_sequence(monkeypatch):
    """验证回调序列 running → completed。"""
    updates: list[str] = []

    async def _noop(code, factory, start_date, end_date):
        pass

    monkeypatch.setattr(watchlist_batch_sync, "_sync_one_stock", _noop)

    async def _update_cb(task_id, status, **kw):
        updates.append(status)

    bg = watchlist_batch_sync.launch_batch_sync("tid-3", ["600519"], None, _update_cb)
    await bg

    assert updates == ["running", "completed"]


# ---------------------------------------------------------------------------
# router POST /api/v1/watchlist/sync
# ---------------------------------------------------------------------------


def _ensure_lock_free():
    """保证 watchlist:sync 锁未占用（测试隔离）。"""
    lk = _get_lock("watchlist:sync")
    while lk.locked():
        lk.release()


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(wl_router.router)
    return app


async def test_sync_endpoint_rejects_empty_group_ids(monkeypatch):
    _ensure_lock_free()
    app = _build_app()

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as ac:
        res = await ac.post("/api/v1/watchlist/sync", json={"group_ids": []})

    assert res.status_code == 400


async def test_sync_endpoint_rejects_missing_group_ids(monkeypatch):
    _ensure_lock_free()
    app = _build_app()

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as ac:
        res = await ac.post("/api/v1/watchlist/sync", json={})

    assert res.status_code == 400


async def test_sync_endpoint_rejects_when_no_stocks(monkeypatch):
    """分组无股票时应返回 400（collect_unique_codes 返回空）。"""
    _ensure_lock_free()
    app = _build_app()

    async def _empty_collect(self, user_id, group_ids):
        return []

    monkeypatch.setattr(wl_router.WatchlistSyncUseCase, "collect_unique_codes", _empty_collect)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as ac:
        res = await ac.post("/api/v1/watchlist/sync", json={"group_ids": [1]})

    assert res.status_code == 400


async def test_sync_endpoint_returns_409_when_locked(monkeypatch):
    """锁占用时应返回 409，且不启动后台任务。"""
    lk = _get_lock("watchlist:sync")
    _ensure_lock_free()
    await lk.acquire()  # 预占锁

    launched = {"count": 0}

    def _fake_launch(*args, **kwargs):
        launched["count"] += 1

    monkeypatch.setattr(wl_router, "launch_batch_sync", _fake_launch)

    app = _build_app()
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as ac:
            res = await ac.post("/api/v1/watchlist/sync", json={"group_ids": [1]})
        assert res.status_code == 409
        assert launched["count"] == 0
    finally:
        if lk.locked():
            lk.release()


async def test_sync_endpoint_success_launches_background(monkeypatch):
    """正常流程：返回 200 + task_id/total，且 launch_batch_sync 被调一次。"""
    _ensure_lock_free()
    app = _build_app()

    async def _collect(self, user_id, group_ids):
        return ["600519", "000001"]

    monkeypatch.setattr(wl_router.WatchlistSyncUseCase, "collect_unique_codes", _collect)

    # mock SyncTaskRepository.create 避免 DB（返回带 task_id 的简单对象）
    class _FakeTask:
        def __init__(self, task_id):
            self.task_id = task_id

    async def _fake_create(self, task):
        return _FakeTask(task.task_id)

    monkeypatch.setattr(wl_router.MySQLSyncTaskRepository, "create", _fake_create)

    launched: list[tuple] = []

    def _fake_launch(task_id, codes, session_factory, update_cb):
        launched.append((task_id, codes))
        # 返回一个不会真跑的伪 task（避免后台任务污染测试）
        import asyncio
        fut = asyncio.get_event_loop().create_future()
        fut.set_result(None)
        return fut

    monkeypatch.setattr(wl_router, "launch_batch_sync", _fake_launch)

    # mock get_db，避免真实 session
    class _FakeDB:
        async def commit(self):
            pass

    async def _fake_get_db():
        yield _FakeDB()

    app.dependency_overrides[wl_router.get_db] = _fake_get_db

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as ac:
        res = await ac.post("/api/v1/watchlist/sync", json={"group_ids": [1, 2]})

    assert res.status_code == 200
    body = res.json()["data"]
    assert body["total"] == 2
    assert body["groups"] == 2
    assert "task_id" in body
    assert len(launched) == 1
    assert launched[0][1] == ["600519", "000001"]

    _ensure_lock_free()  # 清理：端点内部已 acquire，但 fake_launch 没有真实 task 释放
