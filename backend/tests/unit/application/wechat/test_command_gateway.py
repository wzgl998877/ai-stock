"""消息网关测试（specs/010 T003）：鉴权 / 去重 / 非文本忽略 / 授权流转。

全 Fake（research D12）：patch ``app.core.database.async_session``（gateway
函数内 import，patch 源模块属性即生效）与 RedisCache；不触真 DB/网络。
"""

import pytest

import app.core.database as core_db
import app.infrastructure.repositories.mysql_wechat_command_repo as repo_module
from app.application.wechat import command_gateway as gw
from app.application.wechat.command_dispatcher import ReplyChannel

pytestmark = pytest.mark.asyncio


class FakeClient:
    def __init__(self):
        self.sent: list[tuple[str, str]] = []  # (user_id, text)

    async def send_message(self, user_id, text, context_token):
        self.sent.append((user_id, text))

    async def send_text_with_fallback(self, user_id, text, context_token):
        self.sent.append((user_id, text))
        return "mid"


class FakeRepo:
    """create 抛 DuplicateCommandError 的可编程 Fake。"""

    def __init__(self, duplicate=False):
        self.duplicate = duplicate
        self.updates: list = []

    # 兼作 session（gateway 对 ctx yield 对象调 commit/rollback）
    async def commit(self):
        pass

    async def rollback(self):
        pass

    async def create(self, cmd):
        if self.duplicate:
            from app.infrastructure.repositories.mysql_wechat_command_repo import (
                DuplicateCommandError,
            )

            raise DuplicateCommandError(cmd.msg_id)
        cmd.id = 1
        return cmd

    async def update_status(self, cmd_id, status, **kw):
        self.updates.append((cmd_id, status))


class FakeSessionCtx:
    def __init__(self, repo):
        self.repo = repo

    async def __aenter__(self):
        return self.repo

    async def __aexit__(self, *exc):
        return False


def _msg(msg_id="mid-1", user="u@im.wechat", text="跑缠论"):
    return {
        "message_type": 1,
        "from_user_id": user,
        "context_token": "CT",
        "client_id": msg_id,
        "item_list": [{"type": 1, "text_item": {"text": text}}],
    }


@pytest.fixture
def authorized(monkeypatch):
    monkeypatch.setattr(gw.settings, "wechat_cmd_authorized_users", "u@im.wechat")


@pytest.fixture
def fake_repo(monkeypatch):
    """gateway 函数内 import 真 repo 类 → patch 源模块类，注入 FakeRepo。"""
    repo = FakeRepo()
    monkeypatch.setattr(repo_module, "MySQLWeChatCommandRepository", lambda s: repo)
    return repo


async def test_unauthorized_denied_no_task(authorized, monkeypatch):
    client = FakeClient()
    monkeypatch.setattr(gw.settings, "wechat_cmd_authorized_users", "u@im.wechat")

    dispatched = []
    async def _fake_dispatch(*a, **k):
        dispatched.append(a)

    monkeypatch.setattr(gw, "dispatch", _fake_dispatch)
    await gw.handle_command_message(_msg(user="stranger@im.wechat"), client)

    assert len(client.sent) == 1 and "授权名单" in client.sent[0][1]
    assert dispatched == []  # 未授权不产生任何任务（FR-017/US6 场景1）


async def test_duplicate_message_skipped(authorized, fake_repo, monkeypatch):
    client = FakeClient()
    fake_repo.duplicate = True

    routed = []
    async def _fake_resolve(text, history):
        routed.append(text)
        from app.application.wechat.intent_router import IntentResult
        return IntentResult(tool_name="run_chanlun", params={})

    monkeypatch.setattr(gw, "resolve_intent", _fake_resolve)
    await gw.handle_command_message(_msg(), client)

    assert routed == []      # 重复消息不进路由
    assert client.sent == []  # 也不产生回复（静默跳过，FR-004）


async def test_non_text_message_ignored(authorized, monkeypatch):
    client = FakeClient()
    msg = _msg()
    msg["item_list"] = []  # 无文本
    monkeypatch.setattr(core_db, "async_session", lambda: FakeSessionCtx(FakeRepo()))

    routed = []
    monkeypatch.setattr(gw, "resolve_intent", lambda *a: routed.append(a))
    await gw.handle_command_message(msg, client)
    assert routed == []


async def test_authorized_routes_to_dispatcher(authorized, fake_repo, monkeypatch):
    client = FakeClient()

    from app.application.wechat.intent_router import IntentResult

    async def _fake_resolve(text, history):
        return IntentResult(tool_name="chanlun_status", params={}, via="pattern")

    monkeypatch.setattr(gw, "resolve_intent", _fake_resolve)

    calls = []
    async def _fake_dispatch(cmd, tool, params, reply):
        calls.append((tool.name, params, isinstance(reply, ReplyChannel)))

    monkeypatch.setattr(gw, "dispatch", _fake_dispatch)
    await gw.handle_command_message(_msg(text="缠论状态"), client)

    assert len(calls) == 1
    assert calls[0][0] == "chanlun_status"
    assert calls[0][2] is True


async def test_unrecognized_replies_help_and_closes(authorized, fake_repo, monkeypatch):
    client = FakeClient()
    repo = fake_repo

    from app.application.wechat.intent_router import IntentResult

    async def _fake_resolve(text, history):
        return IntentResult(reply_text="我可以执行这些指令：…", via="fallback")

    monkeypatch.setattr(gw, "resolve_intent", _fake_resolve)
    await gw.handle_command_message(_msg(text="今天天气不错"), client)

    assert len(client.sent) == 1 and "指令" in client.sent[0][1]  # HELP 回复
    assert repo.updates and repo.updates[0][1].value == "closed"  # 仅留痕不执行
