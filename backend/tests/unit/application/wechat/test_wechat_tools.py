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

    async def scan(self, period, user_id, trigger_type=None, stock_codes=None):
        self.calls.append(dict(period=period, user_id=user_id,
                               trigger_type=trigger_type, stock_codes=stock_codes))
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

    async def _fake_sync(code, repo):
        if code in fail_codes:
            raise RuntimeError("sina down")
        pulled.append(code)

    monkeypatch.setattr("app.application.sync.chanlun_30m_sync.sync_stock_30m", _fake_sync)
    monkeypatch.setattr(chanlun_tools, "_build_monitor", lambda *a: monitor)

    async def _fake_codes(s):
        return ["002940", "000333", "600132"]

    monkeypatch.setattr(chanlun_tools, "_all_watchlist_codes", _fake_codes)
    return monitor, pulled, fail_codes


async def test_run_chanlun_full_watchlist(monkeypatch, chanlun_env):
    monitor, pulled, _ = chanlun_env
    tool = registry.get("run_chanlun")
    result = await tool.execute(_ctx({}))

    assert monitor.calls[0]["trigger_type"] == "manual"     # 溯源区分定时扫描
    assert monitor.calls[0]["period"] == "m30"
    assert monitor.calls[0]["stock_codes"] == ["002940", "000333", "600132"]
    assert monitor.calls[0]["user_id"] == "wechat"          # 系统短标识（run_log 列宽 String(32)）
    assert sorted(pulled) == ["000333", "002940", "600132"]
    assert "成功 2" in result.summary and DISCLAIMER_SUFFIX in result.summary


async def test_run_chanlun_single_code_via_pattern_params(chanlun_env):
    monitor, pulled, _ = chanlun_env
    tool = registry.get("run_chanlun")
    result = await tool.execute(_ctx({"codes_str": "002940"}))  # 规则层捕获形态

    assert monitor.calls[0]["stock_codes"] == ["002940"]    # 只算指定股票
    assert pulled == ["002940"]


async def test_run_chanlun_pull_failure_not_blocked(chanlun_env):
    monitor, pulled, fail_codes = chanlun_env
    fail_codes.add("600132")  # 单股拉数失败
    tool = registry.get("run_chanlun")
    result = await tool.execute(_ctx({"codes": ["002940", "600132"]}))

    assert monitor.calls[0]["stock_codes"] == ["002940"]    # 失败股不进计算
    assert any(f["code"] == "600132" for f in result.failed_items)  # 明细进 FAIL 文案（dispatcher 拼接）


async def test_run_chanlun_empty_watchlist(monkeypatch, chanlun_env):
    async def _empty(s):
        return []

    monkeypatch.setattr(chanlun_tools, "_all_watchlist_codes", _empty)
    tool = registry.get("run_chanlun")
    result = await tool.execute(_ctx({}))
    assert "自选股为空" in result.summary


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
