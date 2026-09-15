"""缠论调度器单元测试（T028）。

``setup_scheduler`` 仅注册任务、不触发执行（任务函数内才用 ``session_factory``），
故无需真实 DB 即可断言任务注册与 cron 解析。

日线数据前置（拉取 → 到位判定 → 重试）的测试已迁至
``tests/unit/application/test_daily_sync.py``。
"""

from datetime import date, datetime

import pytest

from app.application.sync.daily_sync import DailyPullOutcome, DailyPullResult
from app.domain.services.daily_readiness import judge_daily_readiness
from app.infrastructure.scheduler import chanlun_scheduler
from app.infrastructure.scheduler.chanlun_scheduler import _parse_cron, setup_scheduler

EXPECTED = date(2026, 9, 15)


def test_parse_cron():
    assert _parse_cron("15:40") == (15, 40)
    assert _parse_cron("09:05") == (9, 5)


def test_setup_registers_jobs():
    sched = setup_scheduler(session_factory=lambda: None)
    assert sched is not None
    ids = {j.id for j in sched.get_jobs()}
    assert "chanlun_daily_scan" in ids
    assert "chanlun_m30_scan" in ids


def test_daily_rescan_job_registered():
    """兜底补扫 job：15:40 主跑重试耗尽后，收盘晚些再兜一次。"""
    sched = setup_scheduler(session_factory=lambda: None)
    ids = {j.id for j in sched.get_jobs()}
    assert "chanlun_daily_rescan" in ids


def test_jobs_declare_misfire_grace_time():
    """APScheduler 默认 misfire_grace_time 仅 1 秒：进程在触发点前后重启会
    静默丢掉当天扫描（与 2026-09-14 事故同类的单点）。"""
    sched = setup_scheduler(session_factory=lambda: None)
    jobs = {j.id: j for j in sched.get_jobs()}
    assert jobs["chanlun_daily_scan"].misfire_grace_time == 3600
    assert jobs["chanlun_daily_scan"].max_instances == 1
    assert jobs["chanlun_daily_rescan"].misfire_grace_time == 3600
    assert jobs["chanlun_m30_scan"].misfire_grace_time == 3600


def test_m30_trigger_covers_eight_points():
    """m30 触发器应在 8 个目标时点命中（用 9:30-15:00 外不命中做反向断言）。"""
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
        if expected:
            assert triggered is not None and triggered.hour == h and triggered.minute == m, (
                f"期望 {(h, m)} 命中，实际 {triggered}"
            )
        else:
            assert triggered is None or not (triggered.hour == h and triggered.minute == m), (
                f"期望 {(h, m)} 不命中，实际命中 {triggered}"
            )


# ---------------------------------------------------------------------------
# run_daily_scan 编排：数据前置 → 双版本扫描 → 补推收尾
# ---------------------------------------------------------------------------


class _FakeSession:
    def __init__(self):
        self.commits = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def commit(self):
        self.commits += 1


class _FakeMonitor:
    def __init__(self):
        self.calls: list[dict] = []

    async def scan(self, period, user_id, trigger_type, stock_codes,
                   algo_version=None, preflight=None):
        self.calls.append({
            "period": period, "algo_version": algo_version,
            "preflight": preflight, "codes": list(stock_codes),
        })


def _make_result(codes: list[str], ready: bool) -> DailyPullResult:
    state = "in_place" if ready else "stale"
    outcomes = {
        c: DailyPullOutcome(c, state, source="sina" if ready else "tencent",
                            latest_date=EXPECTED if ready else date(2026, 9, 11))
        for c in codes
    }
    verdict = judge_daily_readiness(
        total=len(codes),
        stale_codes=[] if ready else list(codes),
        failed_codes=[],
        expected_date=EXPECTED,
    )
    return DailyPullResult(
        expected_date=EXPECTED, total=len(codes), outcomes=outcomes,
        attempts=1 if ready else 3, verdict=verdict,
    )


def _daily_job_func(sched):
    return next(j for j in sched.get_jobs() if j.id == "chanlun_daily_scan").func


async def _run_daily_scan(monkeypatch, codes, ready=True, retrier_error=False):
    """装配好全部依赖后执行一次日常扫描，返回 (monitor, sync_calls, retrier_calls)。"""
    monitor = _FakeMonitor()
    sync_calls: list[list[str]] = []
    retrier_calls = {"n": 0}

    async def _fake_codes(session):
        return list(codes)

    async def _fake_sync(session_factory, codes_arg, **kwargs):
        sync_calls.append(list(codes_arg))
        return _make_result(list(codes_arg), ready)

    async def _fake_retrier():
        retrier_calls["n"] += 1
        if retrier_error:
            raise RuntimeError("retrier boom")
        return 0

    monkeypatch.setattr(chanlun_scheduler, "_all_watchlist_codes", _fake_codes)
    monkeypatch.setattr(chanlun_scheduler, "_build_monitor", lambda *a: monitor)
    monkeypatch.setattr(
        "app.application.sync.daily_sync.sync_daily_quotes", _fake_sync
    )
    monkeypatch.setattr(
        "app.application.wechat.chanlun_signal_push.build_signal_retrier",
        lambda *a: _fake_retrier,
    )

    sched = setup_scheduler(session_factory=_FakeSession)
    await _daily_job_func(sched)()
    return monitor, sync_calls, retrier_calls


@pytest.mark.asyncio
async def test_daily_scan_runs_both_versions_once_with_shared_preflight(monkeypatch):
    """双版本各扫一次且共用同一 preflight；数据前置只调一次（重试在其内部）。"""
    monitor, sync_calls, retrier_calls = await _run_daily_scan(
        monkeypatch, ["600000", "000001"], ready=True
    )

    assert sync_calls == [["600000", "000001"]]      # 不在 job 层重试
    assert [c["algo_version"] for c in monitor.calls] == ["1.1.0", "1.0.0"]
    assert all(c["period"] == "daily" for c in monitor.calls)

    preflights = {id(c["preflight"]) for c in monitor.calls}
    assert len(preflights) == 1                       # 两个版本拿到同一个对象
    assert monitor.calls[0]["preflight"].ok is True
    assert retrier_calls["n"] == 1                    # 收尾补推跑了一次


@pytest.mark.asyncio
async def test_daily_scan_marks_preflight_when_data_stale(monkeypatch):
    """数据未到位：preflight 携带 data_stale 与诊断，仍照常扫描。"""
    monitor, _, _ = await _run_daily_scan(
        monkeypatch, ["600000", "000001"], ready=False
    )

    preflight = monitor.calls[0]["preflight"]
    assert preflight.ok is False
    assert preflight.status == "data_stale"
    assert preflight.notes[0]["stock_code"] == "数据前置"
    assert len(monitor.calls) == 2                    # 未到位不跳过扫描


@pytest.mark.asyncio
async def test_daily_scan_skips_when_no_watchlist(monkeypatch):
    monitor, sync_calls, retrier_calls = await _run_daily_scan(monkeypatch, [])

    assert sync_calls == [] and monitor.calls == []
    assert retrier_calls["n"] == 0


@pytest.mark.asyncio
async def test_daily_scan_retrier_failure_is_swallowed(monkeypatch):
    """补推异常不影响扫描 job 正常收尾。"""
    monitor, _, retrier_calls = await _run_daily_scan(
        monkeypatch, ["600000"], ready=True, retrier_error=True
    )

    assert retrier_calls["n"] == 1
    assert len(monitor.calls) == 2                    # 扫描照常完成
