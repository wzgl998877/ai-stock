"""腾讯 iLink Bot HTTP 客户端（微信 ClawBot 背后协议）。

纯协议封装，无业务语义。协议要点（2026-08 实测验证）：

- 基座 ``https://ilinkai.weixin.qq.com``，全部 POST + JSON；
- 认证头：``AuthorizationType: ilink_bot_token`` + ``Authorization: Bearer <bot_token>``
  + ``X-WECHAT-UIN``（base64(str(random_uint32))，**每次请求随机**）+ ``iLink-App-Id``；
- ``getupdates`` 长轮询（服务器挂起约 35s，客户端超时须 > 35s）；
- ``sendmessage`` 必须携带用户最近一条入站消息的 ``context_token``（token 管理见
  ``ilink_token_store`` 与 ``ilink_polling_service``）；
- 错误码：``ret=0`` 成功、``-14`` 会话过期（bot_token 失效，需人工更换）、
  ``-2`` 参数 / context_token 失效。

与行情客户端「异常吞掉返回空」的降级哲学不同：本客户端把协议错误以异常上抛，
由 Application 层决定退避 / 跳过策略。
"""

from __future__ import annotations

import base64
import logging
import os
import struct
import uuid
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

# channel_version / bot_agent 对标官方 wechatbot-sdk 0.3.0 的默认值
_CHANNEL_VERSION = "0.3.0"
_BOT_AGENT = f"WeChatBot/{_CHANNEL_VERSION}"


class ILinkError(Exception):
    """iLink 网关返回 ret != 0 的统称。``code`` 属性携带原始 ret 码。"""

    def __init__(self, message: str, code: int = 0):
        super().__init__(message)
        self.code = code


class ILinkAuthError(ILinkError):
    """ret == -14：会话过期（bot_token 失效），程序无法自愈，需人工更换 token。"""


class ILinkContextError(ILinkError):
    """ret == -2：参数 / context_token 失效（token 过期或请求体非法）。"""


def _random_wechat_uin() -> str:
    """base64(str(random_uint32)) —— 防重放，每次请求重新生成。"""
    val = struct.unpack(">I", os.urandom(4))[0]
    return base64.b64encode(str(val).encode()).decode("ascii")


class ILinkBotClient:
    """iLink Bot 网关客户端（getupdates 长轮询 + sendmessage 发送）。"""

    def __init__(
        self,
        bot_token: str,
        base_url: str = "https://ilinkai.weixin.qq.com",
        client_version: int = 196608,
        poll_timeout: float = 40.0,
        send_timeout: float = 10.0,
    ):
        self.bot_token = bot_token
        self.base_url = base_url.rstrip("/")
        self.client_version = client_version
        # 长轮询客户端超时必须大于服务器 35s 挂起时间
        self.poll_timeout = poll_timeout
        self.send_timeout = send_timeout

    # ------------------------------------------------------------------
    # 公开 API
    # ------------------------------------------------------------------

    async def get_updates(self, get_updates_buf: str) -> tuple[list[dict], str]:
        """长轮询拉取消息。

        Args:
            get_updates_buf: 上次返回的游标；首次传空字符串 ``""``。

        Returns:
            ``(msgs, 新游标)``。新游标是不透明字符串，须在下次调用时原样回传。
        """
        payload = await self._post(
            "/ilink/bot/getupdates",
            {"get_updates_buf": get_updates_buf, "base_info": self._base_info()},
            timeout=self.poll_timeout,
        )
        msgs = payload.get("msgs") or []
        new_buf = payload.get("get_updates_buf") or ""
        return msgs, new_buf

    async def send_message(
        self, to_user_id: str, text: str, context_token: str
    ) -> str:
        """发送文本消息。

        Args:
            to_user_id: 接收人（``xxx@im.wechat``）。
            text: 文本内容（单条上限约 4000 字符，超长由调用方分片）。
            context_token: 用户最近一条入站消息携带的 token（原样回传）。

        Returns:
            网关返回的 ``message_id``（可能为空字符串）。

        Raises:
            ILinkContextError: token 失效（ret=-2）。
            ILinkAuthError: 会话过期（ret=-14）。
        """
        msg = {
            "from_user_id": "",
            "to_user_id": to_user_id,
            "client_id": str(uuid.uuid4()),
            "message_type": 2,   # BOT 方向
            "message_state": 2,  # FINISH（完整消息）
            "context_token": context_token,
            "item_list": [{"type": 1, "text_item": {"text": text}}],
        }
        payload = await self._post(
            "/ilink/bot/sendmessage",
            {"msg": msg, "base_info": self._base_info()},
            timeout=self.send_timeout,
        )
        return str(payload.get("message_id") or "")

    async def send_text_with_fallback(
        self, to_user_id: str, text: str, context_token: str
    ) -> str:
        """带 token 发送；``ret=-2``（token 过期）时降级为 tokenless 重试一次。

        iLink 网关允许空 ``context_token`` 的降级发送（对标 hermes-agent
        PR #17432 对同类问题的修复；2026-08-19 本服务实测 tokenless 请求
        正常返回 message_id）。供信号推送/心跳等**主动消息**场景使用；
        回执等「回复」场景天然持有新鲜 token，直接用 ``send_message``。
        """
        try:
            return await self.send_message(to_user_id, text, context_token)
        except ILinkContextError:
            logger.warning(
                "context_token 失效（ret=-2），降级 tokenless 重试: %s", to_user_id
            )
            return await self.send_message(to_user_id, text, "")

    # ------------------------------------------------------------------
    # 内部
    # ------------------------------------------------------------------

    def _base_info(self) -> dict[str, str]:
        return {"channel_version": _CHANNEL_VERSION, "bot_agent": _BOT_AGENT}

    def _build_headers(self) -> dict[str, str]:
        """认证头集合；``X-WECHAT-UIN`` 每次调用随机生成（防重放）。"""
        return {
            "Content-Type": "application/json",
            "AuthorizationType": "ilink_bot_token",
            "Authorization": f"Bearer {self.bot_token}",
            "X-WECHAT-UIN": _random_wechat_uin(),
            "iLink-App-Id": "bot",
            "iLink-App-ClientVersion": str(self.client_version),
        }

    async def _post(
        self, endpoint: str, body: dict[str, Any], timeout: float
    ) -> dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, json=body, headers=self._build_headers())
            resp.raise_for_status()
        payload = resp.json()
        ret = payload.get("ret")
        if isinstance(ret, int) and ret != 0:
            errmsg = payload.get("errmsg") or f"ret={ret}"
            if ret == -14:
                raise ILinkAuthError(errmsg, code=ret)
            if ret == -2:
                raise ILinkContextError(errmsg, code=ret)
            raise ILinkError(errmsg, code=ret)
        return payload
