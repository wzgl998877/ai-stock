"""指令调度器测试（specs/010 T005）：快/慢分流、单飞 BUSY、ack 时序、终态推送。

patch ``command_dispatcher.async_session`` 与 ``MySQLWeChatCommandRepository``
（均为模块级名字）；FakeClient 记录 send 序列验证两段式时序（research D6）。
"""

import asyncio

import pytest

from app.application.wechat import command_dispatcher as dp
from app.application.wechat.tools.base import ToolContext, ToolResult, WeChatTool
from app.domain.models.wechat_command import CommandStatus, PushStatus, WeChatCommand

pytestmark = pytest.mark.asyncio


class FakeClient:
    def __init__(self, fail_final=False):
        self.sent: list[tuple[str, str]] = []  # (user_id, text) 按时序
        self.fail_final = fail_final

    async def send_message(self, user_id, text, context_token):
        self.sent.append((user_id, text))

    async def send_text_with_fallback(self, user_id, text, context_token):
        if self.fail_final:
            raise RuntimeError("push down")
        self.sent.append((user_id, text))
        return "mid"


class FakeRepo:
    def __init__(self, running=None):
        self.statuses: list[tuple[int, object]] = []
        self.pushed: list[tuple[int, PushStatus]] = []
        self.progress: list[str] = []
        self._running = running or []

    # 兼作 session（dispatcher 直接对 ctx yield 对象调 commit/rollback）
    async def commit(self):
        pass

    async def rollback(self):
        pass

    async def update_status(self, cmd_id, status, **kw):
        self.statuses.append((cmd_id, status))

    async def mark_pushed(self, cmd_id, push):
        self.pushed.append((cmd_id, push))

    async def update_progress(self, cmd_id, progress):
        self.progress.append(progress)

    async def find_running(self, user_id=None, exclude_id=None):
        return [c for c in self._running if c.id != exclude_id]


class FakeSessionCtx:
    def __init__(self, repo):
        self.repo = repo

    async def __aenter__(self):
        return self.repo

    async def __aexit__(self, *exc):
        return False


class FakeFastTool(WeChatTool):
    name = "t_fast"
    description = "测试快工具，用于验证直答链路。"
    kind = "fast"
    fail = False

    async def execute(self, ctx: ToolContext) -> ToolResult:
        if self.fail:
            raise ValueError("boom")
        return ToolResult(summary="快结果", succeeded=1)


class FakeSlowTool(WeChatTool):
    name = "t_slow"
    description = "测试慢工具，用于验证两段式链路。"
    kind = "slow"
    lock_key = "test"
    fail = False

    async def execute(self, ctx: ToolContext) -> ToolResult:
        await ctx.report_progress("1/2")
        if self.fail:
            raise RuntimeError("slow crash")
        return ToolResult(summary="慢结果", succeeded=2)


def _cmd(**kw) -> WeChatCommand:
    base = dict(msg_id="m", user_id="u@im.wechat", raw_text="x")
    base.update(kw)
    cmd = WeChatCommand(**base)
    cmd.id = 99
    return cmd


def _reply(client):
    return dp.ReplyChannel(client=client, user_id="u@im.wechat", context_token="CT")


@pytest.fixture
def patched(monkeypatch):
    repo = FakeRepo()
    monkeypatch.setattr(dp, "async_session", lambda: FakeSessionCtx(repo))
    monkeypatch.setattr(dp, "MySQLWeChatCommandRepository", lambda s: repo)
    return repo


# ---------------------------------------------------------------------------
# 快指令：同步执行，回复即结果（DIRECT_RESULT）
# ---------------------------------------------------------------------------

async def test_fast_tool_direct_reply(patched):
    client = FakeClient()
    await dp.dispatch(_cmd(), FakeFastTool(), {}, _reply(client))

    assert patched.statuses[-1][1] == CommandStatus.COMPLETED
    assert client.sent == [("u@im.wechat", "快结果")]
    assert patched.pushed[-1][1] == PushStatus.PUSHED


async def test_fast_tool_failure_replies_fail(patched):
    client = FakeClient()
    tool = FakeFastTool()
    tool.fail = True
    await dp.dispatch(_cmd(), tool, {}, _reply(client))

    assert patched.statuses[-1][1] == CommandStatus.FAILED   # FR-013 落库
    assert any("执行失败" in t for _, t in client.sent)       # 且告知用户


# ---------------------------------------------------------------------------
# 参数校验：非法代码 → CLARIFY，不执行（FR-009）
# ---------------------------------------------------------------------------

async def test_invalid_codes_get_clarify(patched):
    client = FakeClient()
    await dp.dispatch(_cmd(), FakeFastTool(), {"codes": ["2940"]}, _reply(client))

    assert client.sent and "6 位数字" in client.sent[0][1]
    assert patched.statuses[-1][1] == CommandStatus.CLOSED    # 未执行


# ---------------------------------------------------------------------------
# 慢指令：ACK → 后台执行 → 终态推送（两段式，契约 §3）
# ---------------------------------------------------------------------------

async def test_slow_tool_two_phase_reply(patched):
    client = FakeClient()
    await dp.dispatch(_cmd(), FakeSlowTool(), {}, _reply(client))

    # 第一段：受理确认即时送达
    assert "收到" in client.sent[0][1]
    # 等后台完成
    for _ in range(50):
        await asyncio.sleep(0)
    assert patched.statuses[-1][1] == CommandStatus.COMPLETED
    assert any(t == "慢结果" for _, t in client.sent)          # 第二段：终态推送
    assert patched.pushed[-1][1] == PushStatus.PUSHED
    assert patched.progress == ["1/2"]                         # 进度回写


async def test_slow_tool_busy_replies_progress(monkeypatch):
    repo = FakeRepo(running=[
        WeChatCommand(msg_id="r1", user_id="u@im.wechat", raw_text="跑缠论",
                      tool_name="t_slow", status=CommandStatus.RUNNING, progress="3/10")
    ])
    monkeypatch.setattr(dp, "async_session", lambda: FakeSessionCtx(repo))
    monkeypatch.setattr(dp, "MySQLWeChatCommandRepository", lambda s: repo)

    # 预占锁：模拟同类任务在跑
    from app.application.sync.sync_executor import _get_lock
    lock = _get_lock("wechat_cmd:test")
    await lock.acquire()
    try:
        client = FakeClient()
        await dp.dispatch(_cmd(), FakeSlowTool(), {}, _reply(client))
        assert any("进度 3/10" in t for _, t in client.sent)   # BUSY + 当前进度
        assert repo.statuses[-1][1] == CommandStatus.CLOSED     # 不重复启动
    finally:
        lock.release()


async def test_slow_tool_crash_pushes_fail(patched):
    client = FakeClient()
    tool = FakeSlowTool()
    tool.fail = True
    await dp.dispatch(_cmd(), tool, {}, _reply(client))
    for _ in range(50):
        await asyncio.sleep(0)

    assert patched.statuses[-1][1] == CommandStatus.FAILED
    assert any("任务失败" in t for _, t in client.sent)         # 失败必推（FR-013）


async def test_push_failure_recorded_but_task_completed(patched):
    """推送失败：任务仍 completed，push_status=failed（可查询兜底，SC-003）。"""
    client = FakeClient(fail_final=True)
    await dp.dispatch(_cmd(), FakeSlowTool(), {}, _reply(client))
    for _ in range(50):
        await asyncio.sleep(0)

    assert patched.statuses[-1][1] == CommandStatus.COMPLETED
    assert patched.pushed[-1][1] == PushStatus.FAILED
