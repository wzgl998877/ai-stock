"""微信指令工具测试（specs/010 T015/T018）：缠论三件套的成功/失败/查询三路。

patch 源模块函数（工具内函数内 import，patch 源模块属性即生效）：
``sync_stock_30m``、``chanlun_tools._build_monitor``、``_all_watchlist_codes``、
``MySQLWeChatCommandRepository``（status/history 工具用）。
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

import app.infrastructure.repositories.mysql_wechat_command_repo as repo_module
from app.application.wechat.tools import chanlun_tools, registry
from app.application.wechat.tools.base import DISCLAIMER_SUFFIX, ToolContext
from app.application.wechat.tools.chanlun_tools import ChanlunStatusTool, RunChanlunTool
from app.application.wechat.tools.system_tools import CmdHistoryTool
from app.domain.models.wechat_command import CommandStatus, PushStatus, WeChatCommand

pytestmark = pytest.mark.asyncio


class FakeRunLog:
    id = 7
    total = 3
    success = 2
    failed = 1


class FakeMonitor:
    def __init__(self):
        self.calls: list[dict] = []
        self.fail_versions: set[str] = set()  # 命中即抛，测单版本 scan 异常隔离

    async def scan(self, period, user_id, trigger_type=None, stock_codes=None, algo_version=None):
        if algo_version in self.fail_versions:
            raise RuntimeError("scan boom")
        self.calls.append(dict(period=period, user_id=user_id,
                               trigger_type=trigger_type, stock_codes=stock_codes,
                               algo_version=algo_version))
        return FakeRunLog()


class FakeSession:
    async def commit(self):
        pass

    async def rollback(self):
        pass


class FakeSessionCtx:
    async def __aenter__(self):
        return FakeSession()

    async def __aexit__(self, *exc):
        return False


def _ctx(params, progress_log=None, cmd_id=0) -> ToolContext:
    async def _prog(p):
        if progress_log is not None:
            progress_log.append(p)

    return ToolContext(
        user_id="u@im.wechat", params=params,
        session_factory=lambda: FakeSessionCtx(), report_progress=_prog,
        cmd_id=cmd_id,
    )


# ---------------------------------------------------------------------------
# RunChanlunTool（US1 / T015）
# ---------------------------------------------------------------------------

@pytest.fixture
def chanlun_env(monkeypatch):
    monitor = FakeMonitor()
    pulled: list[str] = []
    fail_codes: set[str] = set()
    daily_calls: list[list[str]] = []
    daily_fail_codes: list[str] = []

    async def _fake_sync(code, repo):
        if code in fail_codes:
            raise RuntimeError("sina down")
        pulled.append(code)

    async def _fake_pull_daily(session_factory, codes, days=30):
        daily_calls.append(list(codes))
        return list(daily_fail_codes)

    monkeypatch.setattr("app.application.sync.chanlun_30m_sync.sync_stock_30m", _fake_sync)
    monkeypatch.setattr(
        "app.infrastructure.scheduler.chanlun_scheduler._pull_daily_quotes", _fake_pull_daily
    )
    monkeypatch.setattr(chanlun_tools, "_build_monitor", lambda *a: monitor)

    async def _fake_codes(s):
        return ["002940", "000333", "600132"]

    monkeypatch.setattr(chanlun_tools, "_all_watchlist_codes", _fake_codes)
    return monitor, pulled, fail_codes, daily_calls, daily_fail_codes


async def test_run_chanlun_full_watchlist(monkeypatch, chanlun_env):
    monitor, pulled, _, daily_calls, _ = chanlun_env
    tool = registry.get("run_chanlun")
    result = await tool.execute(_ctx({}))

    assert len(monitor.calls) == 4  # 双周期 × 双版本
    assert monitor.calls[0]["trigger_type"] == "manual"     # 溯源区分定时扫描
    assert monitor.calls[0]["user_id"] == "wechat"          # 系统短标识（run_log 列宽 String(32)）
    assert sorted(pulled) == ["000333", "002940", "600132"]
    assert daily_calls and sorted(daily_calls[0]) == ["000333", "002940", "600132"]
    assert "成功 2" in result.summary and DISCLAIMER_SUFFIX in result.summary


async def test_run_chanlun_default_runs_both_periods(chanlun_env):
    """不带周期 → 30m + 日线双跑（用户主诉"怕漏"，默认路径必须覆盖日线）。

    双版本后每周期各两轮 scan（v2 主、v1 副），但行情每周期只补一次。
    """
    monitor, pulled, _, daily_calls, _ = chanlun_env
    tool = registry.get("run_chanlun")
    result = await tool.execute(_ctx({}))

    assert [c["period"] for c in monitor.calls] == ["m30", "m30", "daily", "daily"]
    assert daily_calls                                          # 日线补数也触发
    assert len(daily_calls) == 1                                # 双版本不重复补数
    assert len(pulled) == 3                                     # 30m 每股只拉一次
    assert all(c["trigger_type"] == "manual" for c in monitor.calls)
    assert "30m" in result.summary and "日线" in result.summary


async def test_run_chanlun_single_code_via_pattern_params(chanlun_env):
    monitor, pulled, _, _, _ = chanlun_env
    tool = registry.get("run_chanlun")
    await tool.execute(_ctx({"codes_str": "002940"}))  # 规则层捕获形态

    # 不带周期 → 双跑：两轮 scan 都只算指定股票
    assert [c["period"] for c in monitor.calls] == ["m30", "m30", "daily", "daily"]
    assert all(c["stock_codes"] == ["002940"] for c in monitor.calls)
    assert pulled == ["002940"]


async def test_run_chanlun_period_all_runs_both(chanlun_env):
    """回归（2026-08-31）：LLM 层对「帮我跑缠论」这类不带周期的话会填
    period="all"（enum 里的合法值，路由层又过滤空参数），但执行层
    _PERIOD_ALIASES 不含 all → 被当非法值回引导文案，缠论根本没跑。"""
    monitor, _, _, daily_calls, _ = chanlun_env
    tool = registry.get("run_chanlun")
    result = await tool.execute(_ctx({"period": "all"}))

    assert [c["period"] for c in monitor.calls] == ["m30", "m30", "daily", "daily"]  # 双跑
    assert daily_calls
    assert "暂不支持" not in result.summary
    assert "30m" in result.summary and "日线" in result.summary


async def test_run_chanlun_pull_failure_not_blocked(chanlun_env):
    monitor, pulled, fail_codes, _, _ = chanlun_env
    fail_codes.add("600132")  # 单股拉数失败
    tool = registry.get("run_chanlun")
    result = await tool.execute(_ctx({"codes": ["002940", "600132"]}))

    assert monitor.calls[0]["stock_codes"] == ["002940"]    # 失败股不进计算
    assert [f["code"] for f in result.failed_items] == ["600132"]  # 周期粒度只记一次（双版本不重复）
    assert any(f["code"] == "600132" for f in result.failed_items)  # 明细进 FAIL 文案（dispatcher 拼接）


# ---------------------------------------------------------------------------
# 双版本并存（2026-09-08）：version 参数归一化与透传；
# 缺省双跑（2026-09-09）：不带 version → v2+v1 都算，与 settings 默认版解耦
# ---------------------------------------------------------------------------

async def test_run_chanlun_version_v1_normalized_to_1_0_0(chanlun_env):
    """LLM 层 version="v1" → scan 收到规范串 1.0.0；摘要带 (v1) 标签。"""
    monitor, _, _, _, _ = chanlun_env
    tool = registry.get("run_chanlun")
    result = await tool.execute(_ctx({"version": "v1"}))
    assert len(monitor.calls) == 2  # 双周期单版本
    assert all(c["algo_version"] == "1.0.0" for c in monitor.calls)
    assert "（v1）" in result.summary and "（v2）" not in result.summary
    assert result.meta["versions"] == ["v1"]


async def test_run_chanlun_version_from_rule_layer_pattern(chanlun_env):
    """规则层 version_str（「跑缠论 v1」捕获）→ scan 收到 1.0.0。"""
    monitor, _, _, _, _ = chanlun_env
    tool = registry.get("run_chanlun")
    result = await tool.execute(_ctx({"version_str": "v1"}))
    assert all(c["algo_version"] == "1.0.0" for c in monitor.calls)
    assert "（v1）" in result.summary


async def test_run_chanlun_version_v2_explicit(chanlun_env):
    """显式 version="v2" → scan 收到 1.1.0；摘要带 (v2) 标签。"""
    monitor, _, _, _, _ = chanlun_env
    tool = registry.get("run_chanlun")
    result = await tool.execute(_ctx({"version": "v2"}))
    assert len(monitor.calls) == 2  # 双周期单版本
    assert all(c["algo_version"] == "1.1.0" for c in monitor.calls)
    assert "（v2）" in result.summary and "（v1）" not in result.summary
    assert result.meta["versions"] == ["v2"]


async def test_run_chanlun_version_default_runs_both(monkeypatch, chanlun_env):
    """不带 version → v2+v1 双跑（2026-09-09 语义变更：原为 settings 默认单跑）。

    显式把 settings 默认版设为 v1 也不影响——缺省双跑与全局配置解耦，
    网页端/回测入口仍按 settings 取默认版。
    """
    monkeypatch.setattr(chanlun_tools.settings, "chanlun_algo_version", "1.0.0")
    monitor, pulled, _, daily_calls, _ = chanlun_env
    tool = registry.get("run_chanlun")
    result = await tool.execute(_ctx({}))

    assert [(c["period"], c["algo_version"]) for c in monitor.calls] == [
        ("m30", "1.1.0"), ("m30", "1.0.0"),       # v2 主、v1 副（对标定时扫描）
        ("daily", "1.1.0"), ("daily", "1.0.0"),
    ]
    assert "（v2）" in result.summary and "（v1）" in result.summary
    assert result.meta["versions"] == ["v2", "v1"]
    assert len(result.meta["run_log_ids"]) == 4
    assert len(daily_calls) == 1 and len(pulled) == 3  # 行情不因双版本重复拉


async def test_run_chanlun_single_period_default_runs_both_versions(chanlun_env):
    """指定单周期但不指定版本 → 该周期 v2+v1 各一轮，另一周期不跑。"""
    monitor, _, _, daily_calls, _ = chanlun_env
    tool = registry.get("run_chanlun")
    result = await tool.execute(_ctx({"period": "m30"}))

    assert [(c["period"], c["algo_version"]) for c in monitor.calls] == [
        ("m30", "1.1.0"), ("m30", "1.0.0"),
    ]
    assert not daily_calls                                    # 日线补数不触发
    assert "30m" in result.summary


async def test_run_chanlun_explicit_version_with_period_all(chanlun_env):
    """period="all" + 显式 v1 → 双周期单版本，不重复补数。"""
    monitor, pulled, _, daily_calls, _ = chanlun_env
    tool = registry.get("run_chanlun")
    await tool.execute(_ctx({"period": "all", "version": "v1"}))

    assert [(c["period"], c["algo_version"]) for c in monitor.calls] == [
        ("m30", "1.0.0"), ("daily", "1.0.0"),
    ]
    assert len(daily_calls) == 1 and len(pulled) == 3


async def test_run_chanlun_scan_version_failure_isolated(chanlun_env):
    """单版本 scan 抛异常 → 不阻断另一版本与其他周期；摘要提示部分口径失败。"""
    monitor, _, _, _, _ = chanlun_env
    monitor.fail_versions.add("1.0.0")  # v1 两轮全炸
    tool = registry.get("run_chanlun")
    result = await tool.execute(_ctx({}))

    assert [c["algo_version"] for c in monitor.calls] == ["1.1.0", "1.1.0"]  # v2 照常
    assert "部分口径计算失败" in result.summary
    assert "30m（v1）" in result.summary and "日线（v1）" in result.summary
    assert "（v2）" in result.summary                       # 成功轮次的统计仍在
    assert DISCLAIMER_SUFFIX in result.summary
    assert len(result.meta["run_log_ids"]) == 2             # 只有 v2 两轮落 run_log


async def test_run_chanlun_all_versions_failed_summary(chanlun_env):
    """两版本 scan 全失败（补数正常）→ 不误报"数据全部拉取失败"，run_log_ids 为空。"""
    monitor, _, _, _, _ = chanlun_env
    monitor.fail_versions.update({"1.0.0", "1.1.0"})
    tool = registry.get("run_chanlun")
    result = await tool.execute(_ctx({}))

    assert monitor.calls == []
    assert "部分口径计算失败" in result.summary
    assert "数据全部拉取失败" not in result.summary
    assert result.meta["run_log_ids"] == []


async def test_run_chanlun_version_invalid_returns_guidance(chanlun_env):
    """非法 version（v3）→ 回引导文案、不执行 scan。"""
    monitor, _, _, _, _ = chanlun_env
    tool = registry.get("run_chanlun")
    result = await tool.execute(_ctx({"version": "v3"}))
    assert monitor.calls == []
    assert "暂不支持的缠论版本" in result.summary


def test_run_chanlun_pattern_captures_version_str():
    """规则层 pattern 命中「跑缠论 v1」「缠论 v2 日线」「缠论 v1 002940」。"""
    tool = registry.get("run_chanlun")
    assert tool.match_pattern("跑缠论 v1") == {"version_str": "v1"}
    assert tool.match_pattern("缠论 v2 日线") == {"version_str": "v2", "period_str": "日线"}
    assert tool.match_pattern("缠论 v1 002940") == {"version_str": "v1", "codes_str": "002940"}
    # 不带版本仍命中（version_str 缺省）
    assert tool.match_pattern("跑缠论") == {}
    assert tool.match_pattern("缠论 日线") == {"period_str": "日线"}


async def test_run_chanlun_empty_watchlist(monkeypatch, chanlun_env):
    async def _empty(s):
        return []

    monkeypatch.setattr(chanlun_tools, "_all_watchlist_codes", _empty)
    tool = registry.get("run_chanlun")
    result = await tool.execute(_ctx({}))
    assert "自选股为空" in result.summary


# ---------------------------------------------------------------------------
# RunChanlunTool 周期参数（日线支持，D7 预留 P2 增强）
# ---------------------------------------------------------------------------

async def test_run_chanlun_daily_period(chanlun_env):
    monitor, pulled, _, daily_calls, _ = chanlun_env
    tool = registry.get("run_chanlun")
    result = await tool.execute(_ctx({"period_str": "日线"}))  # 规则层捕获形态

    assert [c["period"] for c in monitor.calls] == ["daily", "daily"]  # 单周期双版本
    assert monitor.calls[0]["stock_codes"] == ["002940", "000333", "600132"]
    assert daily_calls and sorted(daily_calls[0]) == ["000333", "002940", "600132"]
    assert len(daily_calls) == 1                              # 双版本不重复补数
    assert not pulled                                    # 30m 补数不应触发
    assert "日线" in result.summary and DISCLAIMER_SUFFIX in result.summary


async def test_run_chanlun_daily_via_llm_period_param(chanlun_env):
    monitor, _, _, daily_calls, _ = chanlun_env
    tool = registry.get("run_chanlun")
    await tool.execute(_ctx({"period": "daily", "codes": ["002940"]}))  # LLM 层产参形态

    assert [c["period"] for c in monitor.calls] == ["daily", "daily"]
    assert monitor.calls[0]["stock_codes"] == ["002940"]
    assert daily_calls and daily_calls[0] == ["002940"]


async def test_run_chanlun_default_is_m30(chanlun_env):
    """显式指定 30m → 只跑 30m，日线补数不触发。"""
    monitor, _, _, daily_calls, _ = chanlun_env
    tool = registry.get("run_chanlun")
    await tool.execute(_ctx({"period_str": "30分钟"}))

    assert [c["period"] for c in monitor.calls] == ["m30", "m30"]  # 单周期双版本
    assert not daily_calls                                # 日线补数不应触发


async def test_run_chanlun_invalid_period_guidance(chanlun_env):
    monitor, _, _, daily_calls, _ = chanlun_env
    tool = registry.get("run_chanlun")
    result = await tool.execute(_ctx({"period": "weekly"}))

    assert "暂不支持的周期" in result.summary
    assert not monitor.calls and not daily_calls          # 不产生任何计算/补数


async def test_run_chanlun_m30_pull_failure_not_blocked(chanlun_env):
    """30m 补数失败的单股只在 30m 轮跳过，日线轮不受污染（各周期独立 failed 集合）。

    双版本后同周期两轮 scan 共享同一 ok_codes；failed_items 按周期只记一次。
    """
    monitor, _, fail_codes, _, _ = chanlun_env
    fail_codes.add("600132")
    tool = registry.get("run_chanlun")
    result = await tool.execute(_ctx({"codes_str": "002940,600132"}))

    by_period = {}
    for c in monitor.calls:
        by_period.setdefault(c["period"], set()).update(c["stock_codes"])
    assert by_period["m30"] == {"002940"}                    # 30m 失败股不进该轮（两版本一致）
    assert by_period["daily"] == {"002940", "600132"}        # 日线未失败照常进
    assert [f["code"] for f in result.failed_items].count("600132") == 1  # 不因双版本重复


async def test_run_chanlun_daily_pull_failure_not_blocked(chanlun_env):
    monitor, _, _, daily_calls, daily_fail_codes = chanlun_env
    daily_fail_codes.append("600132")                     # 日线补数单股失败
    tool = registry.get("run_chanlun")
    result = await tool.execute(_ctx({"period_str": "日线"}))

    assert {c for c in monitor.calls[0]["stock_codes"]} == {"002940", "000333"}  # 失败股不进计算
    assert [f["code"] for f in result.failed_items].count("600132") == 1


# ---------------------------------------------------------------------------
# ChanlunStatusTool / CmdHistoryTool（US2 / T018）
# ---------------------------------------------------------------------------

class FakeCmdRepo:
    def __init__(self, running=None, recent=None):
        self._running = running or []
        self._recent = recent or []
        self.find_running_calls: list[dict] = []

    async def find_running(self, user_id=None, exclude_id=None):
        self.find_running_calls.append(dict(user_id=user_id, exclude_id=exclude_id))
        return self._running

    async def recent_for_user(self, user_id, limit=10, include_closed=False):
        return self._recent


def _record(status, tool="run_chanlun", summary=None, raw="跑缠论", push="pushed"):
    from datetime import datetime

    cmd = WeChatCommand(
        msg_id="x", user_id="u@im.wechat", raw_text=raw, tool_name=tool,
        status=status, result_summary=summary,
        push_status=PushStatus(push) if push else None,
    )
    cmd.create_time = datetime(2026, 8, 21, 14, 30)
    return cmd


async def test_chanlun_status_running(monkeypatch):
    running = _record(CommandStatus.RUNNING, tool="run_chanlun")
    running.progress = "3/10"
    monkeypatch.setattr(repo_module, "MySQLWeChatCommandRepository",
                        lambda s: FakeCmdRepo(running=[running]))
    result = await ChanlunStatusTool().execute(_ctx({}))
    assert "3/10" in result.summary


async def test_chanlun_status_last_result(monkeypatch):
    last = _record(CommandStatus.COMPLETED, summary="缠论 30m 计算完成：共 10 只，成功 10")
    monkeypatch.setattr(repo_module, "MySQLWeChatCommandRepository",
                        lambda s: FakeCmdRepo(recent=[last]))
    result = await ChanlunStatusTool().execute(_ctx({}))
    assert "成功 10" in result.summary


async def test_chanlun_status_idle(monkeypatch):
    monkeypatch.setattr(repo_module, "MySQLWeChatCommandRepository",
                        lambda s: FakeCmdRepo())
    result = await ChanlunStatusTool().execute(_ctx({}))
    assert "没有缠论任务" in result.summary


async def test_chanlun_status_excludes_self(monkeypatch):
    """回归：快指令执行中自身体态是 pending，find_running 必须排除自己。

    生产 bug（2026-08-25 id=5）：「缠论状态」把自己查出来（tool_name 未回写
    为 None）→ 回复「正在执行 None，稍等片刻。」
    """
    repo = FakeCmdRepo()
    monkeypatch.setattr(repo_module, "MySQLWeChatCommandRepository", lambda s: repo)
    result = await ChanlunStatusTool().execute(_ctx({}, cmd_id=5))

    # 1) 查询携带 exclude_id=自己；
    assert repo.find_running_calls and repo.find_running_calls[0]["exclude_id"] == 5
    # 2) 无其他任务时落到「最近一次结果」分支，而非「正在执行 None」。
    assert "正在执行" not in result.summary


async def test_cmd_history_formats_records(monkeypatch):
    records = [
        _record(CommandStatus.COMPLETED, raw="缠论 002940"),
        _record(CommandStatus.FAILED, tool="run_chanlun", raw="跑缠论", push="failed"),
    ]
    monkeypatch.setattr(repo_module, "MySQLWeChatCommandRepository",
                        lambda s: FakeCmdRepo(recent=records))
    result = await CmdHistoryTool().execute(_ctx({}))

    assert "缠论 002940" in result.summary and "已完成" in result.summary
    assert "推送失败" in result.summary  # push_status 可见（US2 场景2）


async def test_cmd_history_empty(monkeypatch):
    monkeypatch.setattr(repo_module, "MySQLWeChatCommandRepository",
                        lambda s: FakeCmdRepo())
    result = await CmdHistoryTool().execute(_ctx({}))
    assert "还没有执行记录" in result.summary
