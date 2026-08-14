"""iLink 长轮询守护服务。

维持 ``getupdates`` 长轮询循环，职责有二：

1. **刷新 context_token**（推送的前提——协议要求回复携带用户最近一条入站
   消息的 token，token 只能靠收消息刷新）；
2. **消息入口**（本期只记日志；未来微信指令路由在此扩展）。

异常恢复：-14 / -2 / 网络错统一指数退避（成功重置）；``CancelledError``
必须重抛（否则任务无法被 cancel）。
"""

from __future__ import annotations

import asyncio
import logging

from app.infrastructure.wechat.ilink_client import (
    ILinkBotClient,
    ILinkError,
)
from app.infrastructure.wechat.ilink_token_store import ILinkTokenStore

logger = logging.getLogger(__name__)

_BACKOFF_INITIAL = 5.0


async def _sleep(seconds: float) -> None:
    """模块级薄封装，便于单元测试 patch（避免 patch 全局 asyncio.sleep 波及测试自身）。"""
    await asyncio.sleep(seconds)


class ILinkPollingService:
    """iLink getupdates 长轮询守护循环。"""

    def __init__(
        self,
        client: ILinkBotClient,
        store: ILinkTokenStore,
        backoff_max: float = 60.0,
    ):
        self.client = client
        self.store = store
        self.backoff_max = backoff_max

    async def run(self) -> None:
        """无限轮询循环；只能通过 task.cancel() 停止。"""
        backoff = _BACKOFF_INITIAL
        while True:
            try:
                cursor = await self.store.get_cursor()
                msgs, new_cursor = await self.client.get_updates(cursor)
                if new_cursor:
                    await self.store.set_cursor(new_cursor)
                for msg in msgs:
                    await self._handle_message(msg)
                backoff = _BACKOFF_INITIAL  # 成功即重置退避
            except asyncio.CancelledError:
                logger.info("iLink 长轮询任务收到停止信号，退出")
                raise
            except ILinkError as e:
                # 含 -14（会话过期，需人工换 token）与 -2（参数/token 失效）：
                # 程序无法自愈，退避重试并保留游标（清了会重放消息）
                logger.error(
                    "iLink 长轮询协议错误(code=%s): %s，%.0fs 后重试", e.code, e, backoff
                )
                await _sleep(backoff)
                backoff = min(backoff * 2, self.backoff_max)
            except (asyncio.TimeoutError, OSError) as e:
                logger.warning("iLink 长轮询网络异常: %s，%.0fs 后重试", e, backoff)
                await _sleep(backoff)
                backoff = min(backoff * 2, self.backoff_max)
            except Exception as e:
                # 兜底：循环绝不能静默死亡
                logger.error("iLink 长轮询未知异常: %s，%.0fs 后重试", e, backoff, exc_info=True)
                await _sleep(backoff)
                backoff = min(backoff * 2, self.backoff_max)

    async def _handle_message(self, msg: dict) -> None:
        """处理一条入站消息：刷新 context_token + 预留指令扩展点。

        ``message_type == 1`` 为用户消息（携带可回传的 context_token）；
        其他为 bot 自身消息回显，跳过。
        """
        if msg.get("message_type") != 1:
            return
        user_id = msg.get("from_user_id") or ""
        context_token = msg.get("context_token") or ""
        if user_id and context_token:
            await self.store.set_context_token(user_id, context_token)
            logger.info("iLink 收到用户消息（from=%s，context_token 已刷新）", user_id)
        # TODO(指令扩展): 解析 text，路由到缠论重算等指令处理器
        logger.debug("iLink 入站消息: %s", msg)


# ---------------------------------------------------------------------------
# 任务生命周期（防 GC，对标 chanlun.py 后台任务模式）
# ---------------------------------------------------------------------------

_polling_tasks: set[asyncio.Task] = set()


def start_polling(service: ILinkPollingService) -> asyncio.Task:
    """启动长轮询后台任务并返回 task 引用（已加入防 GC 集合）。"""
    task = asyncio.create_task(service.run())
    _polling_tasks.add(task)

    def _on_done(t: asyncio.Task) -> None:
        _polling_tasks.discard(t)
        if not t.cancelled() and t.exception() is not None:
            logger.error("iLink 长轮询任务异常退出", exc_info=t.exception())

    task.add_done_callback(_on_done)
    return task


async def stop_polling() -> None:
    """cancel 全部长轮询任务并等待清理完成（shutdown 协作）。"""
    tasks = list(_polling_tasks)
    if not tasks:
        return
    for t in tasks:
        t.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    _polling_tasks.clear()
    logger.info("iLink 长轮询任务已停止")
