"""微信指令消息网关（specs/010）。

由 ``ilink_polling_service._handle_message`` 挂接调用，职责（research D1/D3/D10）：

1. **鉴权**：发送者须在授权白名单（空则回落推送接收人本人），未授权回 DENY 不产生任务；
2. **文本提取**：``item_list[0].text_item.text``（iLink 消息结构，research F1）；
3. **幂等**：按 ``msg_id``（client_id）insert，撞唯一索引即重复消息静默跳过；
4. **会话装配**：读 Redis DialogContext（最近 5 轮，供路由指代消解）；
5. 交 ``intent_router`` 解析 → ``command_dispatcher`` 执行。

任何异常在本层消化（轮询循环绝不能被指令处理拖死）。
"""

from __future__ import annotations

import logging

from app.application.wechat.command_dispatcher import ReplyChannel, dispatch
from app.application.wechat.intent_router import resolve_intent
from app.application.wechat.tools import registry  # 包级 import：触发工具注册
from app.core.config import settings
from app.domain.models.wechat_command import CommandStatus, WeChatCommand
from app.infrastructure.wechat.ilink_client import ILinkBotClient

logger = logging.getLogger(__name__)

# 会话上下文（data-model.md §3）：最近 5 轮 / TTL 30min / RedisCache 自动降级
DIALOG_TURNS = 5
DIALOG_TTL_SECONDS = 30 * 60
DIALOG_KEY_PREFIX = "wechat:cmd:dialog:"

DENY_TEXT = "抱歉，你不在本助手的授权名单内，无法执行指令。"


def _authorized_user_ids() -> set[str]:
    """授权白名单：逗号分隔配置；空则回落推送接收人本人（research D10）。"""
    raw = settings.wechat_cmd_authorized_users.strip()
    if not raw:
        raw = settings.wechat_ilink_user_id
    return {u.strip() for u in raw.split(",") if u.strip()}


def _extract_text(msg: dict) -> str:
    """提取文本：item_list[0].text_item.text（缺失返回空）。"""
    for item in msg.get("item_list") or []:
        text_item = item.get("text_item") or {}
        text = (text_item.get("text") or "").strip()
        if text:
            return text
    return ""


async def _load_dialog(user_id: str) -> list[dict]:
    """读会话上下文；Redis 降级时返回空（仅退化为单轮对话）。"""
    try:
        from app.infrastructure.cache.redis_cache import RedisCache

        cache = RedisCache()
        data = await cache.get(f"{DIALOG_KEY_PREFIX}{user_id}")
        return data if isinstance(data, list) else []
    except Exception:  # noqa: BLE001 - 会话读取失败不阻断指令
        return []


async def _append_dialog(user_id: str, turn: dict) -> None:
    """追加一轮对话（保留最近 N 轮，滑动 TTL）。失败静默。"""
    try:
        import json

        from app.infrastructure.cache.redis_cache import RedisCache

        cache = RedisCache()
        key = f"{DIALOG_KEY_PREFIX}{user_id}"
        data = await cache.get(key)
        turns = data if isinstance(data, list) else []
        turns.append(turn)
        turns = turns[-DIALOG_TURNS:]
        await cache.set(key, turns, ttl=DIALOG_TTL_SECONDS)
    except Exception:  # noqa: BLE001
        pass


async def handle_command_message(msg: dict, client: ILinkBotClient) -> None:
    """处理一条入站用户消息（message_type==1 已由调用方过滤）。

    全链路异常都在此消化，绝不向轮询循环抛出。
    """
    user_id = msg.get("from_user_id") or ""
    context_token = msg.get("context_token") or ""
    msg_id = msg.get("client_id") or ""
    text = _extract_text(msg)

    if not user_id or not msg_id:
        return

    reply = ReplyChannel(client=client, user_id=user_id, context_token=context_token)

    # 1) 鉴权：未授权仅留痕不执行（DENY 不产生任务，spec US6 场景1）
    if user_id not in _authorized_user_ids():
        logger.warning("微信指令：未授权发送者 %s", user_id)
        await reply.send(DENY_TEXT)
        return

    if not text:
        return  # 非文本消息忽略（契约 §4）

    # 2) 幂等受理（撞唯一索引=重复消息，静默跳过）
    from app.core.database import async_session
    from app.infrastructure.repositories.mysql_wechat_command_repo import (
        DuplicateCommandError,
        MySQLWeChatCommandRepository,
    )

    async with async_session() as session:
        repo = MySQLWeChatCommandRepository(session)
        try:
            cmd = await repo.create(
                WeChatCommand(msg_id=msg_id, user_id=user_id, raw_text=text)
            )
            await session.commit()
        except DuplicateCommandError:
            await session.rollback()
            logger.info("微信指令：重复消息跳过 msg_id=%s", msg_id)
            return

    # 3) 意图解析（规则 → LLM → 降级链）
    history = await _load_dialog(user_id)
    intent = await resolve_intent(text, history)

    # 4) 分派：未识别（chat/help）由 router 生成回复文案，dispatcher 统一回
    tool = registry.get(intent.tool_name) if intent.tool_name else None
    if tool is None:
        # chat 兜底 / 帮助 / 降级 —— 仅留痕
        async with async_session() as session:
            repo = MySQLWeChatCommandRepository(session)
            try:
                await repo.update_status(
                    cmd.id, CommandStatus.CLOSED, tool_name=intent.tool_name
                )
                await session.commit()
            except Exception:  # noqa: BLE001
                await session.rollback()
        await reply.send(intent.reply_text or "")
        await _append_dialog(
            user_id,
            {
                "role": "assistant",
                "text": intent.reply_text or "",
                "tool_call": None,
            },
        )
        return

    await _append_dialog(
        user_id,
        {
            "role": "user",
            "text": text,
            "tool_call": {"name": tool.name, "params": intent.params},
        },
    )
    await dispatch(cmd, tool, intent.params, reply)
