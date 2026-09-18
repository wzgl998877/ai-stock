"""iLink context_token 心跳保活用例。

背景（2026-08-19 排查实证）：``context_token`` 仅在用户给 bot 发消息时刷新，
网关侧有效期约 24 小时；过期后 ``sendmessage`` 被拒（ret=-2），信号推送全部
中断，且无主动通道告知用户。当时推断 token 为**滑动过期**（最后使用 +24h），
定时发送心跳即可续期。

**2026-09-18 证伪**：9/16 08:30 心跳成功"使用"了 token，但 9/16 14:18
（= 用户 9/15 14:18 发消息 +24h）窗口照样关闭、推送开始被拒——窗口锚定
用户发消息时刻**固定过期**，bot 发消息不续期，反而消耗窗口内 10 条主动
消息配额。故 ``settings.wechat_keepalive_enabled`` 默认改为 False，本用例
仅作手动开启的发送链路探测（成功=链路通，失败=窗口关闭需用户发消息）。
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from app.infrastructure.wechat.ilink_client import ILinkBotClient
from app.infrastructure.wechat.ilink_token_store import ILinkTokenStore

logger = logging.getLogger(__name__)

# 工具型简洁文案（对标回执文案风格）；日期让接收方可感知心跳新鲜度。
# 默认不再定时发送（见模块 docstring），此文案仅供手动探测链路时使用。
HEARTBEAT_TEXT = "监控在线 · {date}"


class ILinkKeepaliveUseCase:
    """发送一条心跳消息以维持 context_token 活性（单接收人）。"""

    def __init__(
        self,
        client: ILinkBotClient,
        store: ILinkTokenStore,
        to_user_id: str,
    ):
        self.client = client
        self.store = store
        self.to_user_id = to_user_id

    async def send(self) -> bool:
        """发送心跳；返回是否成功。任何失败只记日志，不向上抛。"""
        try:
            context_token = await self.store.get_context_token(self.to_user_id)
            if not context_token:
                logger.warning(
                    "iLink 心跳跳过：无 %s 的 context_token（需接收人先给 bot 发送一条消息激活）",
                    self.to_user_id,
                )
                return False

            text = HEARTBEAT_TEXT.format(date=datetime.now().strftime("%m-%d %H:%M"))
            message_id = await self.client.send_text_with_fallback(
                self.to_user_id, text, context_token
            )
            logger.info("iLink 心跳已发送（message_id=%s）", message_id)
            return True
        except Exception:
            logger.warning(
                "iLink 心跳发送失败：token 可能已过期，信号推送将中断——"
                "需接收人给 bot 发送一条消息重新激活",
                exc_info=True,
            )
            return False


def build_keepalive() -> Optional[ILinkKeepaliveUseCase]:
    """按 settings 装配心跳用例；未启用推送返回 ``None``。"""
    from app.core.config import settings

    if (
        not settings.wechat_push_enabled
        or not settings.wechat_keepalive_enabled
        or not settings.wechat_ilink_bot_token
        or not settings.wechat_ilink_user_id
    ):
        return None

    return ILinkKeepaliveUseCase(
        client=ILinkBotClient(
            bot_token=settings.wechat_ilink_bot_token,
            base_url=settings.wechat_ilink_base_url,
            client_version=settings.wechat_ilink_client_version,
        ),
        store=ILinkTokenStore(),
        to_user_id=settings.wechat_ilink_user_id,
    )
