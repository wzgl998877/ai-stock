"""ChanlunSignalPushUseCase / format_signals_message 单元测试。"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

import pytest

from app.application.wechat.chanlun_signal_push import (
    ChanlunSignalPushUseCase,
    format_signals_message,
)
from app.domain.entities.chanlun import ChanlunSignal
from app.infrastructure.wechat.ilink_client import ILinkContextError

pytestmark = pytest.mark.asyncio


def _sig(**kw) -> ChanlunSignal:
    base = dict(
        stock_code="600519",
        period="m30",
        signal_type="buy2",
        structure_level="stroke",
        signal_time=datetime(2026, 8, 14, 14, 30),
        trigger_price=Decimal("1700.00"),
    )
    base.update(kw)
    return ChanlunSignal(**base)


class FakeClient:
    def __init__(self, fail: Optional[Exception] = None, message_id: str = "MSG-001"):
        self.sent: list[tuple[str, str, str]] = []
        self.fail = fail
        self.message_id = message_id

    async def send_message(self, to_user_id, text, context_token):
        if self.fail:
            raise self.fail
        self.sent.append((to_user_id, text, context_token))
        return self.message_id


class FakeStore:
    def __init__(self, token: Optional[str] = "CTX"):
        self.token = token

    async def get_context_token(self, user_id):
        return self.token

    async def set_context_token(self, user_id, token):
        self.token = token


# ---------------------------------------------------------------------------
# format_signals_message 纯函数
# ---------------------------------------------------------------------------

def test_format_with_names_and_multiple_signals():
    s1 = _sig(stock_code="600519", signal_type="buy2", structure_level="stroke")
    s2 = _sig(
        stock_code="000858", signal_type="sell1", structure_level="segment",
        trigger_price=Decimal("128.50"),
    )
    text = format_signals_message([s1, s2], {"600519": "贵州茅台", "000858": "五粮液"})
    lines = text.splitlines()
    assert lines[0] == "【缠论信号】30分钟周期 · 新增2"
    # 按时间倒序（同刻则稳定），两行都包含代码+名称+标签
    body = "\n".join(lines[1:-1])
    assert "600519 贵州茅台 二买(笔) 1700.00 08-14 14:30" in body
    assert "000858 五粮液 一卖(线段) 128.50 08-14 14:30" in body
    assert "不构成投资建议" in lines[-1]


def test_format_falls_back_to_code_without_name():
    text = format_signals_message([_sig()], {})
    assert "600519" in text
    assert "贵州茅台" not in text


def test_format_empty_signals():
    text = format_signals_message([])
    assert "新增0" in text


def test_format_missing_price_and_time():
    s = _sig(trigger_price=None, signal_time=None)
    text = format_signals_message([s])
    assert "None" not in text


# ---------------------------------------------------------------------------
# push 用例
# ---------------------------------------------------------------------------

async def test_push_sends_aggregated_message():
    client, store = FakeClient(), FakeStore()
    uc = ChanlunSignalPushUseCase(client, store, "u@im.wechat")
    await uc.push([_sig(), _sig(stock_code="000858")])

    assert len(client.sent) == 1
    to, text, ct = client.sent[0]
    assert to == "u@im.wechat"
    assert ct == "CTX"
    assert "新增2" in text


async def test_push_empty_signals_noop():
    client = FakeClient()
    uc = ChanlunSignalPushUseCase(client, FakeStore(), "u@im.wechat")
    await uc.push([])
    assert client.sent == []


async def test_push_skips_without_context_token():
    client = FakeClient()
    uc = ChanlunSignalPushUseCase(client, FakeStore(token=None), "u@im.wechat")
    await uc.push([_sig()])  # 只记 warning，不抛
    assert client.sent == []


async def test_push_swallows_send_failure():
    client = FakeClient(fail=ILinkContextError("prepare failed", code=-2))
    uc = ChanlunSignalPushUseCase(client, FakeStore(), "u@im.wechat")
    await uc.push([_sig()])  # 失败安全：不向上抛
    assert client.sent == []


async def test_push_uses_name_lookup():
    async def lookup(codes):
        assert codes == ["600519"]
        return {"600519": "贵州茅台"}

    client = FakeClient()
    uc = ChanlunSignalPushUseCase(client, FakeStore(), "u@im.wechat", name_lookup=lookup)
    await uc.push([_sig()])
    assert "贵州茅台" in client.sent[0][1]


async def test_push_name_lookup_failure_falls_back():
    async def lookup(codes):
        raise RuntimeError("db down")

    client = FakeClient()
    uc = ChanlunSignalPushUseCase(client, FakeStore(), "u@im.wechat", name_lookup=lookup)
    await uc.push([_sig()])
    assert "600519" in client.sent[0][1]


# ---------------------------------------------------------------------------
# 推送结果回写（push_status / push_message_id）
# ---------------------------------------------------------------------------

class FakeResultWriter:
    def __init__(self, fail: Optional[Exception] = None):
        self.calls: list[tuple[list[int], str, Optional[str]]] = []
        self.fail = fail

    async def __call__(self, ids, status, message_id):
        if self.fail:
            raise self.fail
        self.calls.append((list(ids), status, message_id))


async def test_push_success_records_message_id():
    writer = FakeResultWriter()
    s1, s2 = _sig(id=11), _sig(stock_code="000858", id=12)
    uc = ChanlunSignalPushUseCase(
        FakeClient(), FakeStore(), "u@im.wechat", result_writer=writer
    )
    await uc.push([s1, s2])
    assert writer.calls == [([11, 12], "success", "MSG-001")]


async def test_push_skip_without_token_records_skipped():
    writer = FakeResultWriter()
    uc = ChanlunSignalPushUseCase(
        FakeClient(), FakeStore(token=None), "u@im.wechat", result_writer=writer
    )
    await uc.push([_sig(id=21)])
    assert writer.calls == [([21], "skipped", None)]


async def test_push_send_failure_records_failed():
    writer = FakeResultWriter()
    uc = ChanlunSignalPushUseCase(
        FakeClient(fail=ILinkContextError("prepare failed", code=-2)),
        FakeStore(),
        "u@im.wechat",
        result_writer=writer,
    )
    await uc.push([_sig(id=31)])
    assert writer.calls == [([31], "failed", None)]


async def test_push_without_signal_ids_not_recorded():
    writer = FakeResultWriter()
    uc = ChanlunSignalPushUseCase(
        FakeClient(), FakeStore(), "u@im.wechat", result_writer=writer
    )
    await uc.push([_sig()])  # id=None（如推送器未走 upsert 回填路径）
    assert writer.calls == []


async def test_push_result_writer_failure_swallowed():
    writer = FakeResultWriter(fail=RuntimeError("db down"))
    client = FakeClient()
    uc = ChanlunSignalPushUseCase(
        client, FakeStore(), "u@im.wechat", result_writer=writer
    )
    await uc.push([_sig(id=41)])  # 回写失败不影响发送结果，也不向上抛
    assert len(client.sent) == 1
