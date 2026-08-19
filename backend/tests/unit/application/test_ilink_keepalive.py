"""ILinkKeepaliveUseCase 单元测试：心跳成功 / 无 token 跳过 / 发送失败三分支。"""

from typing import Optional

import pytest

from app.application.wechat.ilink_keepalive import (
    HEARTBEAT_TEXT,
    ILinkKeepaliveUseCase,
)
from app.infrastructure.wechat.ilink_client import ILinkContextError

pytestmark = pytest.mark.asyncio


class FakeClient:
    def __init__(self, fail: Optional[Exception] = None):
        self.sent: list[tuple[str, str, str]] = []
        self.fail = fail

    async def send_message(self, to_user_id, text, context_token):
        if self.fail:
            raise self.fail
        self.sent.append((to_user_id, text, context_token))
        return "MSG-KA"


class FakeStore:
    def __init__(self, token: Optional[str] = "CTX"):
        self.token = token

    async def get_context_token(self, user_id):
        return self.token


async def test_send_uses_current_token():
    client = FakeClient()
    uc = ILinkKeepaliveUseCase(client, FakeStore(), "u@im.wechat")
    assert await uc.send() is True
    to, text, ct = client.sent[0]
    assert to == "u@im.wechat"
    assert ct == "CTX"
    assert text.startswith("监控在线 · ")  # 工具型简洁文案 + 日期


async def test_send_skips_without_token():
    client = FakeClient()
    uc = ILinkKeepaliveUseCase(client, FakeStore(token=None), "u@im.wechat")
    assert await uc.send() is False  # 只记 warning，不抛
    assert client.sent == []


async def test_send_swallows_failure():
    client = FakeClient(fail=ILinkContextError("prepare failed", code=-2))
    uc = ILinkKeepaliveUseCase(client, FakeStore(), "u@im.wechat")
    assert await uc.send() is False  # 失败安全：不向上抛（调度层兜底日志）


def test_heartbeat_text_format():
    assert HEARTBEAT_TEXT.format(date="08-19 08:30") == "监控在线 · 08-19 08:30"
