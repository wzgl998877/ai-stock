"""ILinkPollingService 单元测试（Fake client 可编程序列，patch asyncio.sleep）。"""

import asyncio
from unittest.mock import patch

import pytest

from app.application.wechat.ilink_polling_service import (
    ILinkPollingService,
    start_polling,
    stop_polling,
)
from app.infrastructure.wechat.ilink_client import ILinkAuthError, ILinkError

pytestmark = pytest.mark.asyncio


class FakeClient:
    """可编程响应序列：依次弹出；耗尽后抛 StopLoop（测试用哨兵）。"""

    def __init__(self, responses: list):
        self.responses = list(responses)
        self.calls: list[str] = []
        self.acks: list[tuple[str, str, str]] = []  # (to_user_id, text, context_token)
        self.ack_fail: Exception | None = None

    async def get_updates(self, buf):
        self.calls.append(buf)
        if not self.responses:
            raise StopLoop()
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        # 与真实客户端同构：返回 (msgs, 新游标)
        return item.get("msgs") or [], item.get("get_updates_buf") or ""

    async def send_message(self, to_user_id, text, context_token):
        if self.ack_fail:
            raise self.ack_fail
        self.acks.append((to_user_id, text, context_token))


class StopLoop(Exception):
    """驱动 run() 退出的哨兵（走未知异常兜底分支后由外层捕获）。"""


class FakeStore:
    def __init__(self):
        self.tokens: dict[str, str] = {}
        self.cursor_val: str = ""

    async def get_cursor(self):
        return self.cursor_val

    async def set_cursor(self, buf):
        self.cursor_val = buf

    async def get_context_token(self, user_id):
        return self.tokens.get(user_id)

    async def set_context_token(self, user_id, token):
        self.tokens[user_id] = token


async def _run_until_stop(service, max_s=1.0):
    """跑 run() 直到 StopLoop 哨兵（被未知异常兜底捕获后继续，需外层 cancel）。"""
    task = asyncio.create_task(service.run())
    try:
        await asyncio.wait_for(task, timeout=max_s)
    except (asyncio.TimeoutError, StopLoop):
        pass
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)


async def test_one_round_updates_cursor_and_token():
    msg = {"message_type": 1, "from_user_id": "u@im.wechat", "context_token": "CT1"}
    client = FakeClient([{"msgs": [msg], "get_updates_buf": "BUF2"}])
    store = FakeStore()
    svc = ILinkPollingService(client, store)

    task = asyncio.create_task(svc.run())
    await asyncio.sleep(0.05)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)

    assert store.cursor_val == "BUF2"
    assert store.tokens["u@im.wechat"] == "CT1"
    # 收到用户消息后立即回执
    assert len(client.acks) == 1
    to, text, ct = client.acks[0]
    assert to == "u@im.wechat" and ct == "CT1"
    assert "已收到" in text


async def test_bot_echo_message_skipped():
    """message_type != 1（bot 回显）不刷新 token、不回执。"""
    echo = {"message_type": 2, "from_user_id": "bot@im.bot", "context_token": "X"}
    client = FakeClient([{"msgs": [echo], "get_updates_buf": "B"}])
    store = FakeStore()
    svc = ILinkPollingService(client, store)

    task = asyncio.create_task(svc.run())
    await asyncio.sleep(0.05)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)

    assert store.tokens == {}
    assert client.acks == []


async def test_ack_failure_does_not_break_loop():
    """回执发送失败只记 warning，token 刷新不受影响，循环继续。"""
    from app.infrastructure.wechat.ilink_client import ILinkError

    msg = {"message_type": 1, "from_user_id": "u@im.wechat", "context_token": "CT1"}
    client = FakeClient([{"msgs": [msg], "get_updates_buf": "B2"}])
    client.ack_fail = ILinkError("send failed", code=-99)
    store = FakeStore()
    svc = ILinkPollingService(client, store)

    task = asyncio.create_task(svc.run())
    await asyncio.sleep(0.05)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)

    # token 仍刷新成功
    assert store.tokens["u@im.wechat"] == "CT1"


async def test_auth_error_backoff_and_cursor_kept():
    """-14 走退避重试（5s→10s→20s 指数），游标不清空。"""
    client = FakeClient([ILinkAuthError("session timeout", code=-14)] * 10)
    store = FakeStore()
    store.cursor_val = "KEEP"
    svc = ILinkPollingService(client, store)

    sleeps: list[float] = []

    async def fake_sleep(s):
        sleeps.append(s)
        # 记满 4 档后取消 run 所在任务（CancelledError 会正确穿透 except 链）
        if len(sleeps) >= 4:
            asyncio.current_task().cancel()
            await asyncio.sleep(0)  # 让 cancel 生效

    with patch(
        "app.application.wechat.ilink_polling_service._sleep", fake_sleep
    ):
        task = asyncio.create_task(svc.run())
        for _ in range(500):
            if task.done():
                break
            await asyncio.sleep(0)
        if not task.done():
            task.cancel()
        await asyncio.gather(task, return_exceptions=True)

    assert sleeps[:3] == [5.0, 10.0, 20.0]
    assert store.cursor_val == "KEEP"


async def test_start_and_stop_polling_clean_shutdown():
    """stop_polling 能干净取消任务（CancelledError 不泄漏）。"""
    client = FakeClient([])  # 立即耗尽 → StopLoop 兜底分支
    store = FakeStore()
    svc = ILinkPollingService(client, store)

    async def fake_sleep(s):
        # 必须有真实 await 点，否则飞转循环无法响应 cancel
        await asyncio.sleep(0)

    with patch("app.application.wechat.ilink_polling_service._sleep", fake_sleep):
        task = start_polling(svc)
        await asyncio.sleep(0.05)
        await stop_polling()

    assert task.cancelled() or task.done()
