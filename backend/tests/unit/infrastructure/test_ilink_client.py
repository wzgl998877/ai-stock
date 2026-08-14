"""ILinkBotClient 单元测试（mock httpx，只验证协议封装逻辑）。"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.infrastructure.wechat.ilink_client import (
    ILinkAuthError,
    ILinkBotClient,
    ILinkContextError,
    ILinkError,
)


def _mock_response(payload: dict, status: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = payload
    resp.raise_for_status.return_value = None
    return resp


def _mock_http_client(resp: MagicMock) -> MagicMock:
    """构造可 async with 的 httpx.AsyncClient mock，捕获 post 调用。"""
    client = MagicMock()
    client.post = AsyncMock(return_value=resp)
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=client)
    ctx.__aexit__ = AsyncMock(return_value=False)
    patched = MagicMock(return_value=ctx)
    patched._client = client
    return patched


@pytest.mark.asyncio
async def test_get_updates_parses_msgs_and_cursor():
    payload = {"msgs": [{"a": 1}], "get_updates_buf": "NEWTOKEN=="}
    patched = _mock_http_client(_mock_response(payload))
    with patch("app.infrastructure.wechat.ilink_client.httpx.AsyncClient", patched):
        client = ILinkBotClient(bot_token="tok")
        msgs, buf = await client.get_updates("OLD==")

    assert msgs == [{"a": 1}]
    assert buf == "NEWTOKEN=="
    # 请求体：游标 + base_info（post 以 json= 关键字传参）
    call = patched._client.post.call_args
    body = call.kwargs["json"]
    assert body["get_updates_buf"] == "OLD=="
    assert body["base_info"]["channel_version"]


@pytest.mark.asyncio
async def test_auth_headers_random_uin_each_call():
    """X-WECHAT-UIN 每次请求必须重新随机生成（防重放）。"""
    payload = {"ret": 0, "msgs": []}
    patched = _mock_http_client(_mock_response(payload))
    with patch("app.infrastructure.wechat.ilink_client.httpx.AsyncClient", patched):
        client = ILinkBotClient(bot_token="tok")
        await client.get_updates("")
        await client.get_updates("x")

    headers = [c.kwargs["headers"] for c in patched._client.post.call_args_list]
    assert len(headers) == 2
    assert headers[0]["X-WECHAT-UIN"] != headers[1]["X-WECHAT-UIN"]
    for h in headers:
        assert h["AuthorizationType"] == "ilink_bot_token"
        assert h["Authorization"] == "Bearer tok"
        assert h["iLink-App-Id"] == "bot"


@pytest.mark.asyncio
async def test_send_message_body_structure():
    payload = {"ret": 0, "message_id": "123"}
    patched = _mock_http_client(_mock_response(payload))
    with patch("app.infrastructure.wechat.ilink_client.httpx.AsyncClient", patched):
        client = ILinkBotClient(bot_token="tok")
        mid = await client.send_message("u@im.wechat", "你好", "CTX")

    assert mid == "123"
    call = patched._client.post.call_args
    assert call.args[0].endswith("/ilink/bot/sendmessage")
    body = call.kwargs["json"]
    msg = body["msg"]
    assert msg["to_user_id"] == "u@im.wechat"
    assert msg["from_user_id"] == ""
    assert msg["message_type"] == 2
    assert msg["message_state"] == 2
    assert msg["context_token"] == "CTX"
    # client_id 是 uuid4 格式
    assert len(msg["client_id"].split("-")) == 5
    assert msg["item_list"] == [{"type": 1, "text_item": {"text": "你好"}}]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "ret,exc",
    [
        (-14, ILinkAuthError),
        (-2, ILinkContextError),
        (-99, ILinkError),
    ],
)
async def test_error_codes_raise_typed_exceptions(ret, exc):
    patched = _mock_http_client(_mock_response({"ret": ret, "errmsg": "bad"}))
    with patch("app.infrastructure.wechat.ilink_client.httpx.AsyncClient", patched):
        client = ILinkBotClient(bot_token="tok")
        with pytest.raises(exc) as ei:
            await client.send_message("u", "t", "CTX")
        assert ei.value.code == ret


@pytest.mark.asyncio
async def test_ret_zero_and_missing_both_pass():
    """ret=0 正常；响应缺 ret 字段（如部分网关空响应）也不应误判为错误。"""
    patched = _mock_http_client(_mock_response({"msgs": [], "get_updates_buf": "b"}))
    with patch("app.infrastructure.wechat.ilink_client.httpx.AsyncClient", patched):
        client = ILinkBotClient(bot_token="tok")
        msgs, buf = await client.get_updates("")
        assert msgs == [] and buf == "b"
