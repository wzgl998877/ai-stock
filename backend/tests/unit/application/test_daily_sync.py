"""日线拉取与到位校验单元测试（daily_sync）。

从 ``tests/unit/infrastructure/test_chanlun_scheduler.py`` 迁入——拉取流程已从
调度器（Infrastructure）移到 ``app.application.sync.daily_sync``（Application）。

patch 手法：函数体内 import 的模块按**源模块路径** patch
（如 ``app.application.sync.sina_sync_client.SinaSyncClient``）；重试循环的
``sleep`` 走参数注入，不 patch 全局 ``asyncio.sleep``。
"""

from datetime import date, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from app.application.sync import daily_sync
from app.application.sync.daily_sync import pull_daily_quotes, sync_daily_quotes

pytestmark = pytest.mark.asyncio


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
    latest_by_code = {}  # code -> 最新日K日期（None=无历史）

    def __init__(self, session):
        self.session = session
        self.upserted = []
        _FakeRepo.instances.append(self)

    async def upsert_daily_batch(self, quotes):
        self.upserted.append(quotes)

    async def get_latest_daily_date(self, code, period="daily", source=None):
        return _FakeRepo.latest_by_code.get(code)


@pytest.fixture(autouse=True)
def _reset_fakes():
    _FakeRepo.instances = []
    _FakeRepo.latest_by_code = {}
    yield


def _factory(sessions: list):
    def factory():
        s = _FakeSession()
        sessions.append(s)
        return s

    return factory


# ---------------------------------------------------------------------------
# 迁移自 test_chanlun_scheduler.py 的 pull 用例
# ---------------------------------------------------------------------------


async def test_pull_daily_quotes_upserts_and_clears_cache():
    """正常路径：拉取 → 清洗 → upsert → 清缓存 → commit。"""
    sessions = []
    factory = _factory(sessions)
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
        await pull_daily_quotes(factory, ["600000", "000001"])

    # 增量窗口查询 + 落库各开一次 session/repo（2 股 × 2 次 = 4）
    assert len(_FakeRepo.instances) == 4
    assert all(inst.upserted == [raw] for inst in _FakeRepo.instances if inst.upserted)
    assert set(cleared) == {("600000", "daily"), ("000001", "daily")}
    assert len([s for s in sessions if s.committed]) == 2


async def test_pull_daily_quotes_fallback_to_tencent():
    """降级链：新浪空返回（被限流）→ 腾讯日K兜底，按窗口过滤后落库。"""
    _FakeRepo.latest_by_code = {"600000": date(2026, 8, 24)}
    sessions = []
    factory = _factory(sessions)

    class _FakeSina:
        def fetch_daily_quote(self, code, start_date, end_date, period="daily"):
            return []  # 被限流：HTTP 200 空数组

    tencent_calls: list[dict] = []

    class _FakeTencent:
        async def fetch(self, code, period="daily", count=None):
            tencent_calls.append(dict(code=code, period=period, count=count))
            return [
                {"trade_date": "2026-08-24", "open": "10.0", "close": "10.1"},   # 窗口内
                {"trade_date": "2026-08-25", "open": "10.2", "close": "10.3"},   # 窗口内
                {"trade_date": "2026-08-10", "open": "9.0", "close": "9.1"},     # 窗口外：剔除
            ]

    with patch("app.application.sync.sina_sync_client.SinaSyncClient", _FakeSina), \
         patch("app.infrastructure.market.tencent_kline_client.TencentKlineClient", _FakeTencent), \
         patch("app.domain.services.data_cleaner.clean_daily_quote", side_effect=lambda r, s: r), \
         patch(
             "app.infrastructure.repositories.mysql_stock_data_repo.MySQLStockDataRepository",
             _FakeRepo,
         ), \
         patch("app.application.sync.sync_executor._clear_kline_cache"):
        await pull_daily_quotes(factory, ["600000"])

    assert len(tencent_calls) == 1 and tencent_calls[0]["period"] == "daily"
    # 窗口过滤生效：只落库 08-24 之后的数据
    upserted = next(inst.upserted[0] for inst in _FakeRepo.instances if inst.upserted)
    assert [q["trade_date"] for q in upserted] == ["2026-08-24", "2026-08-25"]


async def test_pull_daily_quotes_single_failure_not_blocking():
    """单股网络异常 → 记 warning，不影响其他股；落库异常走 rollback。"""
    sessions = []
    factory = _factory(sessions)

    class _FakeSina:
        def fetch_daily_quote(self, code, start_date, end_date, period="daily"):
            if code == "BAD001":
                raise RuntimeError("network down")
            return [{"code": code, "trade_date": "2026-08-14"}]

    class _FailingRepo:
        def __init__(self, session):
            self.session = session

        async def get_latest_daily_date(self, code, period="daily", source=None):
            return None

        async def upsert_daily_batch(self, quotes):
            raise RuntimeError("db error")

    with patch("app.application.sync.sina_sync_client.SinaSyncClient", _FakeSina), \
         patch("app.domain.services.data_cleaner.clean_daily_quote", side_effect=lambda r, s: r), \
         patch(
             "app.infrastructure.repositories.mysql_stock_data_repo.MySQLStockDataRepository",
             _FailingRepo,
         ), \
         patch("app.application.sync.sync_executor._clear_kline_cache"):
        await pull_daily_quotes(factory, ["BAD001", "600000"])  # 不抛

    # BAD001 网络异常在 gather 结果里被记日志；600000 落库失败 rollback。
    # 增量查询 session 未 commit 也未 rollback（只读），故 rollback 的必是落库 session
    assert any(s.rolled_back for s in sessions)


async def test_pull_daily_quotes_dirty_rows_skipped():
    """清洗失败的脏数据跳过；全部脏 → 不落库。"""
    sessions = []
    factory = _factory(sessions)

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
        await pull_daily_quotes(factory, ["600000"])

    assert all(not s.committed for s in sessions)  # 无净数据 → 无落库 commit
    assert all(not inst.upserted for inst in _FakeRepo.instances)


async def test_pull_daily_quotes_deadlock_retry():
    """死锁 1213 重试：第一次死锁、第二次成功 → 最终 commit。"""
    sessions = []
    factory = _factory(sessions)
    raw = [{"code": "000858", "trade_date": "2026-08-27", "close": "71.0"}]

    class _FakeSina:
        def fetch_daily_quote(self, code, start_date, end_date, period="daily"):
            return raw

    calls = {"n": 0}

    class _DeadlockOnceRepo(_FakeRepo):
        async def upsert_daily_batch(self, quotes):
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError(
                    "(pymysql.err.OperationalError) (1213, "
                    "'Deadlock found when trying to get lock; "
                    "try restarting transaction')"
                )
            return await super().upsert_daily_batch(quotes)

    with patch("app.application.sync.sina_sync_client.SinaSyncClient", _FakeSina), \
         patch("app.domain.services.data_cleaner.clean_daily_quote", side_effect=lambda r, s: r), \
         patch(
             "app.infrastructure.repositories.mysql_stock_data_repo.MySQLStockDataRepository",
             _DeadlockOnceRepo,
         ), \
         patch("app.application.sync.sync_executor._clear_kline_cache"), \
         patch("asyncio.sleep", new_callable=AsyncMock):
        await pull_daily_quotes(factory, ["000858"])

    assert calls["n"] == 2                      # 死锁后重试了一次
    assert any(s.committed for s in sessions)   # 最终成功


async def test_pull_daily_quotes_non_deadlock_no_retry():
    """非死锁异常不重试：一次失败直接标 failed。"""
    sessions = []
    factory = _factory(sessions)

    class _FakeSina:
        def fetch_daily_quote(self, code, start_date, end_date, period="daily"):
            return [{"code": code, "trade_date": "2026-08-27"}]

    calls = {"n": 0}

    class _AlwaysFailRepo(_FakeRepo):
        async def upsert_daily_batch(self, quotes):
            calls["n"] += 1
            raise RuntimeError("db error")

    with patch("app.application.sync.sina_sync_client.SinaSyncClient", _FakeSina), \
         patch("app.domain.services.data_cleaner.clean_daily_quote", side_effect=lambda r, s: r), \
         patch(
             "app.infrastructure.repositories.mysql_stock_data_repo.MySQLStockDataRepository",
             _AlwaysFailRepo,
         ), \
         patch("app.application.sync.sync_executor._clear_kline_cache"):
        result = await pull_daily_quotes(factory, ["600000"])

    assert calls["n"] == 1                      # 不重试
    assert not any(s.committed for s in sessions)
    assert result.outcomes["600000"].state == "failed"
    assert "db error" in result.outcomes["600000"].error


async def test_pull_daily_quotes_incremental_window():
    """增量窗口：库中有历史 → 从库内最新日期起拉；无历史 → 默认 30 自然日窗口。"""
    _FakeRepo.latest_by_code = {"600000": date(2026, 8, 22)}
    sessions = []
    factory = _factory(sessions)
    captured: dict = {}

    class _FakeSina:
        def fetch_daily_quote(self, code, start_date, end_date, period="daily"):
            captured[code] = (start_date, end_date)
            return [{"code": code, "trade_date": "2026-08-25"}]

    with patch("app.application.sync.sina_sync_client.SinaSyncClient", _FakeSina), \
         patch("app.domain.services.data_cleaner.clean_daily_quote", side_effect=lambda r, s: r), \
         patch(
             "app.infrastructure.repositories.mysql_stock_data_repo.MySQLStockDataRepository",
             _FakeRepo,
         ), \
         patch("app.application.sync.sync_executor._clear_kline_cache"):
        await pull_daily_quotes(factory, ["600000", "000001"])

    assert captured["600000"][0] == "2026-08-22"
    expected_start = (date.today() - timedelta(days=30)).strftime("%Y-%m-%d")
    assert captured["000001"][0] == expected_start


# ---------------------------------------------------------------------------
# 数据源标记与到位判定（2026-09-14 事故回归）
# ---------------------------------------------------------------------------


async def test_fetch_daily_raw_source_three_states():
    """``_fetch_daily_raw`` 的 source 三态：sina / tencent（含空行）/ ""（两源皆空）。"""
    class _SinaWithData:
        def fetch_daily_quote(self, code, start_date, end_date, period="daily"):
            return [{"trade_date": "2026-09-15"}]

    class _SinaEmpty:
        def fetch_daily_quote(self, code, start_date, end_date, period="daily"):
            return []

    class _TencentWithRows:
        async def fetch(self, code, period="daily", count=None):
            return [{"trade_date": "2026-09-11"}]

    class _TencentEmpty:
        async def fetch(self, code, period="daily", count=None):
            return []

    with patch("app.application.sync.sina_sync_client.SinaSyncClient", _SinaWithData):
        rows, source = await daily_sync._fetch_daily_raw("600000", "2026-09-01", "2026-09-15")
    assert source == "sina" and rows

    with patch("app.application.sync.sina_sync_client.SinaSyncClient", _SinaEmpty), \
         patch("app.infrastructure.market.tencent_kline_client.TencentKlineClient", _TencentWithRows):
        rows, source = await daily_sync._fetch_daily_raw("600000", "2026-09-01", "2026-09-15")
    assert source == "tencent" and [r["trade_date"] for r in rows] == ["2026-09-11"]

    # 腾讯有返回但行全在窗口外 → source 仍为 tencent、rows 为空（源活着但没新数据）
    with patch("app.application.sync.sina_sync_client.SinaSyncClient", _SinaEmpty), \
         patch("app.infrastructure.market.tencent_kline_client.TencentKlineClient", _TencentWithRows):
        rows, source = await daily_sync._fetch_daily_raw("600000", "2026-09-12", "2026-09-15")
    assert source == "tencent" and rows == []

    with patch("app.application.sync.sina_sync_client.SinaSyncClient", _SinaEmpty), \
         patch("app.infrastructure.market.tencent_kline_client.TencentKlineClient", _TencentEmpty):
        rows, source = await daily_sync._fetch_daily_raw("600000", "2026-09-01", "2026-09-15")
    assert source == "" and rows == []


async def test_pull_daily_quotes_marks_actual_source():
    """腾讯降级的数据 must 标 data_source='tencent'（原实现恒传 "sina"）。"""
    sessions = []
    factory = _factory(sessions)
    seen_sources: list[str] = []

    class _FakeSina:
        def fetch_daily_quote(self, code, start_date, end_date, period="daily"):
            return []

    class _FakeTencent:
        async def fetch(self, code, period="daily", count=None):
            return [{"trade_date": "2026-09-15"}]

    def recording_cleaner(row, source):
        seen_sources.append(source)
        return row

    with patch("app.application.sync.sina_sync_client.SinaSyncClient", _FakeSina), \
         patch("app.infrastructure.market.tencent_kline_client.TencentKlineClient", _FakeTencent), \
         patch("app.domain.services.data_cleaner.clean_daily_quote", recording_cleaner), \
         patch(
             "app.infrastructure.repositories.mysql_stock_data_repo.MySQLStockDataRepository",
             _FakeRepo,
         ), \
         patch("app.application.sync.sync_executor._clear_kline_cache"):
        await pull_daily_quotes(factory, ["600000"])

    assert seen_sources == ["tencent"]


async def test_pull_daily_quotes_stale_when_fallback_has_no_new_rows():
    """事故复现：新浪 456 + 腾讯只给旧数据 → state=stale、source=tencent。

    旧实现在这条路径上既不抛异常也不进失败列表，被静默当作成功。
    """
    _FakeRepo.latest_by_code = {"300929": date(2026, 9, 11)}
    sessions = []
    factory = _factory(sessions)

    class _FakeSina:
        def fetch_daily_quote(self, code, start_date, end_date, period="daily"):
            return []  # HTTP 456 被吞成空

    class _FakeTencent:
        async def fetch(self, code, period="daily", count=None):
            # 数据未更新：最新仍停在 09-11，窗口过滤后无新行
            return [{"trade_date": "2026-09-11"}, {"trade_date": "2026-09-10"}]

    with patch("app.application.sync.sina_sync_client.SinaSyncClient", _FakeSina), \
         patch("app.infrastructure.market.tencent_kline_client.TencentKlineClient", _FakeTencent), \
         patch("app.domain.services.data_cleaner.clean_daily_quote", side_effect=lambda r, s: r), \
         patch(
             "app.infrastructure.repositories.mysql_stock_data_repo.MySQLStockDataRepository",
             _FakeRepo,
         ), \
         patch("app.application.sync.sync_executor._clear_kline_cache"):
        result = await pull_daily_quotes(
            factory, ["300929"], expected=date(2026, 9, 14)
        )

    outcome = result.outcomes["300929"]
    assert outcome.state == "stale"
    assert outcome.source == "tencent"
    assert outcome.latest_date == date(2026, 9, 11)
    assert result.ready is False


async def test_pull_daily_quotes_in_place_when_latest_reaches_expected():
    """库内已推进到期望日期 → in_place（两源皆空也不误报）。"""
    _FakeRepo.latest_by_code = {"300929": date(2026, 9, 15)}
    sessions = []
    factory = _factory(sessions)

    class _FakeSina:
        def fetch_daily_quote(self, code, start_date, end_date, period="daily"):
            return []

    class _FakeTencent:
        async def fetch(self, code, period="daily", count=None):
            return []

    with patch("app.application.sync.sina_sync_client.SinaSyncClient", _FakeSina), \
         patch("app.infrastructure.market.tencent_kline_client.TencentKlineClient", _FakeTencent), \
         patch("app.domain.services.data_cleaner.clean_daily_quote", side_effect=lambda r, s: r), \
         patch(
             "app.infrastructure.repositories.mysql_stock_data_repo.MySQLStockDataRepository",
             _FakeRepo,
         ), \
         patch("app.application.sync.sync_executor._clear_kline_cache"):
        result = await pull_daily_quotes(
            factory, ["300929"], expected=date(2026, 9, 15)
        )

    assert result.outcomes["300929"].state == "in_place"
    assert result.ready is True


# ---------------------------------------------------------------------------
# sync_daily_quotes：带到位校验的重试循环
# ---------------------------------------------------------------------------


def _patch_pull_rounds(monkeypatch, states_by_round: list[str]):
    """按轮次返回指定 state 的假 pull；记录每轮实际请求的 code。"""
    rounds: list[list[str]] = []

    async def fake_pull(session_factory, codes, days=30, *, expected=None, concurrency=None):
        rounds.append(list(codes))
        state = states_by_round[min(len(rounds) - 1, len(states_by_round) - 1)]
        return daily_sync.DailyPullResult(
            expected_date=expected,
            total=len(codes),
            outcomes={
                code: daily_sync.DailyPullOutcome(code, state, source="sina")
                for code in codes
            },
        )

    monkeypatch.setattr(daily_sync, "pull_daily_quotes", fake_pull)
    return rounds


async def _run_sync(monkeypatch, codes, states, **kwargs):
    rounds = _patch_pull_rounds(monkeypatch, states)
    sleeps: list[float] = []

    async def fake_sleep(seconds):
        sleeps.append(seconds)

    result = await sync_daily_quotes(
        lambda: None, codes, max_attempts=kwargs.pop("max_attempts", 3),
        retry_interval=10, sleep=fake_sleep, **kwargs,
    )
    return result, rounds, sleeps


async def test_sync_ready_first_round_stops_immediately(monkeypatch):
    result, rounds, sleeps = await _run_sync(monkeypatch, ["a", "b"], ["in_place"])

    assert rounds == [["a", "b"]]
    assert result.attempts == 1
    assert result.ready is True
    assert sleeps == []          # 首轮到位 → 不空等


async def test_sync_retries_only_pending_codes(monkeypatch):
    """未到位 → 重试，且第二轮只重拉上一轮 stale 的股票。"""
    rounds = []

    async def fake_pull(session_factory, codes, days=30, *, expected=None, concurrency=None):
        rounds.append(list(codes))
        state = "stale" if len(rounds) == 1 else "in_place"
        return daily_sync.DailyPullResult(
            expected_date=expected,
            total=len(codes),
            outcomes={
                code: daily_sync.DailyPullOutcome(code, state, source="sina")
                for code in codes
            },
        )

    monkeypatch.setattr(daily_sync, "pull_daily_quotes", fake_pull)
    sleeps: list[float] = []

    async def fake_sleep(seconds):
        sleeps.append(seconds)

    result = await sync_daily_quotes(
        lambda: None, ["a", "b", "c"], max_attempts=3, retry_interval=20, sleep=fake_sleep
    )

    assert rounds == [["a", "b", "c"], ["a", "b", "c"]]
    assert result.attempts == 2
    assert result.ready is True
    assert sleeps == [20]


async def test_sync_stops_when_partial_stale_below_threshold(monkeypatch):
    """41 只中仅 1 只未到位（疑似停牌）→ 不触发重试，不空等。"""
    codes = [f"c{i:03d}" for i in range(40)] + ["suspended"]

    async def fake_pull(session_factory, codes_arg, days=30, *, expected=None, concurrency=None):
        return daily_sync.DailyPullResult(
            expected_date=expected,
            total=len(codes_arg),
            outcomes={
                code: daily_sync.DailyPullOutcome(
                    code, "stale" if code == "suspended" else "in_place", source="sina"
                )
                for code in codes_arg
            },
        )

    monkeypatch.setattr(daily_sync, "pull_daily_quotes", fake_pull)
    sleeps: list[float] = []

    async def fake_sleep(seconds):
        sleeps.append(seconds)

    result = await sync_daily_quotes(
        lambda: None, codes, max_attempts=3, retry_interval=20, sleep=fake_sleep
    )

    assert result.attempts == 1
    assert result.ready is False
    assert result.verdict.should_retry is False
    assert sleeps == []


async def test_sync_exhausts_attempts_on_persistent_outage(monkeypatch):
    result, rounds, sleeps = await _run_sync(
        monkeypatch, ["a", "b"], ["stale"], max_attempts=3
    )

    assert result.attempts == 3
    assert len(rounds) == 3
    assert sleeps == [10, 10]
    assert result.verdict.should_retry is True   # 耗尽后仍如实标记
    assert result.ready is False


async def test_sync_empty_codes_returns_early(monkeypatch):
    result, rounds, sleeps = await _run_sync(monkeypatch, [], ["in_place"])

    assert result.total == 0
    assert result.attempts == 0
    assert rounds == []


# ---------------------------------------------------------------------------
# to_preflight：写进 run_log 的诊断
# ---------------------------------------------------------------------------


def _result_with(states: dict, attempts: int = 1):
    outcomes = {
        code: daily_sync.DailyPullOutcome(
            code, state, source=source, latest_date=latest
        )
        for code, (state, source, latest) in states.items()
    }
    verdict = daily_sync.judge_daily_readiness(
        total=len(states),
        stale_codes=[c for c, (s, _, _) in states.items() if s == "stale"],
        failed_codes=[c for c, (s, _, _) in states.items() if s == "failed"],
        expected_date=date(2026, 9, 14),
    )
    return daily_sync.DailyPullResult(
        expected_date=date(2026, 9, 14),
        total=len(states),
        outcomes=outcomes,
        attempts=attempts,
        verdict=verdict,
    )


async def test_preflight_ok_when_all_in_place():
    result = _result_with({"a": ("in_place", "sina", date(2026, 9, 14))})
    preflight = result.to_preflight()

    assert preflight.ok is True
    assert preflight.status is None
    assert preflight.notes == []


async def test_preflight_summarizes_outage_with_reason_shapes():
    """故障时首条是汇总，逐股 reason 区分「无返回」与「未更新」两种形态。"""
    result = _result_with({
        "300929": ("stale", "tencent", date(2026, 9, 11)),   # 源活着但数据旧
        "000429": ("stale", "", date(2026, 9, 10)),          # 两源皆无返回
    })
    preflight = result.to_preflight()

    assert preflight.ok is False
    assert preflight.status == "data_stale"
    head = preflight.notes[0]
    assert head["stock_code"] == "数据前置"
    assert "未到位 2/2" in head["reason"] and "2026-09-14" in head["reason"]

    reasons = {n["stock_code"]: n["reason"] for n in preflight.notes[1:]}
    assert "未更新" in reasons["300929"] and "tencent" in reasons["300929"]
    assert "无返回" in reasons["000429"]
    # 形状保持 {stock_code, reason}，前端零改动即可渲染
    assert all("stock_code" in n and "reason" in n for n in preflight.notes)


async def test_preflight_reports_failure_reason_and_truncates():
    states = {f"c{i}": ("failed", "", None) for i in range(15)}
    preflight = _result_with(states).to_preflight(max_notes=5)

    # 汇总 1 条 + 截断后的 5 条明细
    assert len(preflight.notes) == 6
    assert "拉取/落库失败" in preflight.notes[1]["reason"]
