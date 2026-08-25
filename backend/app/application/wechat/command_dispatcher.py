"""指令调度器（specs/010，research D5/D6）：快/慢分流、单飞、两段式应答、终态回推。

- **快指令**（kind=fast）：同步执行直达 completed，回复即结果（DIRECT_RESULT）；
- **慢指令**（kind=slow）：同类单飞（复用 ``sync_executor._get_lock``）→ 秒回 ACK
  （``send_message``，token 新鲜）→ ``asyncio.create_task`` 后台执行 → 终态推送
  ``send_text_with_fallback``（token 可能已过期，tokenless 降级保送达尝试）；
- 重复触发同类慢指令 → 回复当前进度（BUSY），不重复启动；
- 工具异常兜底：记 failed + 推 FAIL，禁止静默（spec FR-013）；
- 回复通道由 dispatcher 独占，工具内不得直接 send（contracts §2）。
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass

from app.application.wechat.tools.base import ToolContext, ToolResult, WeChatTool
from app.core.database import async_session
from app.domain.models.wechat_command import CommandStatus, PushStatus, WeChatCommand
from app.infrastructure.repositories.mysql_wechat_command_repo import (
    MySQLWeChatCommandRepository,
)
from app.infrastructure.wechat.ilink_client import ILinkBotClient

logger = logging.getLogger(__name__)

# 慢指令整体兜底超时（30 分钟；缠论/同步正常分钟级完成）
SLOW_TASK_TIMEOUT_SECONDS = 30 * 60

_CODE_RE = re.compile(r"^\d{6}$")


@dataclass
class ReplyChannel:
    """回复通道：受理场景用新鲜 token；终态推送允许 tokenless 降级（research D6）。"""

    client: ILinkBotClient
    user_id: str
    context_token: str

    async def send(self, text: str) -> bool:
        """即时回复（ACK/快指令结果）：token 新鲜，失败返回 False。"""
        try:
            await self.client.send_message(self.user_id, text, self.context_token)
            return True
        except Exception:  # noqa: BLE001 - 回复失败不阻断流程，结果仍落库可查
            logger.warning("微信指令回复发送失败 user=%s", self.user_id, exc_info=True)
            return False

    async def send_final(self, text: str) -> PushStatus:
        """终态推送：token 过期自动降级 tokenless，返回推送结果状态。"""
        try:
            await self.client.send_text_with_fallback(self.user_id, text, self.context_token)
            return PushStatus.PUSHED
        except Exception:  # noqa: BLE001
            logger.error("微信指令终态推送失败 user=%s", self.user_id, exc_info=True)
            return PushStatus.FAILED


def _validate_params(tool: WeChatTool, params: dict) -> str | None:
    """参数校验（FR-009）：非法时返回 CLARIFY 文案，合法返回 None。"""
    codes = params.get("codes")
    if codes is not None:
        if not isinstance(codes, list):
            codes = [codes]
        bad = [c for c in codes if not _CODE_RE.match(str(c))]
        if bad:
            return f"股票代码格式不对：{','.join(bad)}（应为 6 位数字）。请确认后再发，例如「缠论 002940」。"
        params["codes"] = [str(c) for c in codes]
    return None


async def _noop_progress(_: str) -> None:  # 快指令默认进度回调为 no-op
    return None


async def dispatch(
    cmd: WeChatCommand, tool: WeChatTool, params: dict, reply: ReplyChannel
) -> None:
    """指令分派入口（网关调用）。参数在进入前已由路由产出。"""
    # 参数校验：非法 → CLARIFY，不执行
    clarify = _validate_params(tool, params)
    if clarify:
        async with async_session() as s:
            repo = MySQLWeChatCommandRepository(s)
            try:
                await repo.update_status(
                    cmd.id, CommandStatus.CLOSED, tool_name=tool.name, params=params
                )
                await s.commit()
            except Exception:  # noqa: BLE001
                await s.rollback()
        await reply.send(clarify)
        return

    if tool.kind == "fast":
        await _run_fast(cmd, tool, params, reply)
    else:
        await _launch_slow(cmd, tool, params, reply)


# ---------------------------------------------------------------------------
# 快指令：同步执行，回复即结果
# ---------------------------------------------------------------------------

async def _run_fast(
    cmd: WeChatCommand, tool: WeChatTool, params: dict, reply: ReplyChannel
) -> None:
    try:
        result = await tool.execute(
            ToolContext(
                user_id=cmd.user_id,
                params=params,
                session_factory=async_session,
                report_progress=_noop_progress,
                cmd_id=cmd.id or 0,
            )
        )
        async with async_session() as s:
            repo = MySQLWeChatCommandRepository(s)
            await repo.update_status(
                cmd.id,
                CommandStatus.COMPLETED,
                tool_name=tool.name,
                params=params,
                result_summary=result.summary,
            )
            await s.commit()
        # 快指令的回复即推送：送达即 pushed，失败记 failed（可查询兜底）
        push = PushStatus.PUSHED if await reply.send(result.summary) else PushStatus.FAILED
        async with async_session() as s:
            repo = MySQLWeChatCommandRepository(s)
            try:
                await repo.mark_pushed(cmd.id, push)
                await s.commit()
            except Exception:  # noqa: BLE001
                await s.rollback()
    except Exception as e:  # noqa: BLE001 - 快指令异常也要让用户知道（FR-013）
        logger.error("微信指令快工具 %s 执行失败: %s", tool.name, e, exc_info=True)
        fail_text = f"执行失败：{e}"[:2000]
        async with async_session() as s:
            repo = MySQLWeChatCommandRepository(s)
            try:
                await repo.update_status(
                    cmd.id,
                    CommandStatus.FAILED,
                    tool_name=tool.name,
                    params=params,
                    error_message=str(e),
                )
                await s.commit()
            except Exception:  # noqa: BLE001
                await s.rollback()
        await reply.send(fail_text)


# ---------------------------------------------------------------------------
# 慢指令：单飞 + ACK + 后台执行 + 终态推送
# ---------------------------------------------------------------------------

async def _busy_reply(cmd: WeChatCommand, reply: ReplyChannel) -> None:
    """同类任务在跑：回复当前进度，不重复启动（FR-011）。"""
    async with async_session() as s:
        repo = MySQLWeChatCommandRepository(s)
        running = await repo.find_running(user_id=cmd.user_id, exclude_id=cmd.id)
    current = running[0] if running else None
    if current and current.progress:
        text = f"已有任务在执行（{current.tool_name}），进度 {current.progress}。可用「执行记录」随时查看。"
    elif current:
        text = f"已有任务在执行（{current.tool_name}），稍等片刻。可用「执行记录」随时查看。"
    else:
        text = "已有同类任务在执行，请稍后再试。"
    # 本条消息：未启动新任务，留痕 closed
    async with async_session() as s:
        repo = MySQLWeChatCommandRepository(s)
        try:
            await repo.update_status(cmd.id, CommandStatus.CLOSED)
            await s.commit()
        except Exception:  # noqa: BLE001
            await s.rollback()
    await reply.send(text)


async def _launch_slow(
    cmd: WeChatCommand, tool: WeChatTool, params: dict, reply: ReplyChannel
) -> None:
    from app.application.sync.sync_executor import _get_lock

    lock = _get_lock(f"wechat_cmd:{tool.lock_key}") if tool.lock_key else None
    if lock is not None and lock.locked():
        await _busy_reply(cmd, reply)
        return

    if lock is not None:
        await lock.acquire()

    # 状态 → running + ACK（受理确认，契约 §2）
    async with async_session() as s:
        repo = MySQLWeChatCommandRepository(s)
        try:
            await repo.update_status(
                cmd.id, CommandStatus.RUNNING, tool_name=tool.name, params=params
            )
            await s.commit()
        except Exception:  # noqa: BLE001
            await s.rollback()
    scope = params.get("codes") or "全部自选股"
    await reply.send(f"收到，开始{tool.description.split('，')[0]}（范围：{scope}）。完成后会推送结果，也可发「执行记录」查看进度。")

    async def _run() -> None:
        try:
            await asyncio.wait_for(
                _execute_slow_and_push(cmd, tool, params, reply),
                timeout=SLOW_TASK_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            logger.error("微信指令慢工具 %s 超时（%ss）", tool.name, SLOW_TASK_TIMEOUT_SECONDS)
            await _finalize_failed(cmd, tool, reply, f"任务超时（>{SLOW_TASK_TIMEOUT_SECONDS // 60} 分钟）已中止")
        except Exception as e:  # noqa: BLE001
            logger.error("微信指令慢工具 %s 异常: %s", tool.name, e, exc_info=True)
            await _finalize_failed(cmd, tool, reply, str(e))
        finally:
            if lock is not None and lock.locked():
                lock.release()

    # 防 GC（对标 launch_batch_sync 范式）
    _background: set[asyncio.Task] = set()
    task = asyncio.create_task(_run())
    _background.add(task)
    task.add_done_callback(_background.discard)


async def _execute_slow_and_push(
    cmd: WeChatCommand, tool: WeChatTool, params: dict, reply: ReplyChannel
) -> None:
    """执行慢工具 → 落终态 → 终态推送 → 回写 push_status。"""

    async def _report(progress: str) -> None:
        async with async_session() as s:
            repo = MySQLWeChatCommandRepository(s)
            try:
                await repo.update_progress(cmd.id, progress)
                await s.commit()
            except Exception:  # noqa: BLE001
                await s.rollback()

    result: ToolResult = await tool.execute(
        ToolContext(
            user_id=cmd.user_id,
            params=params,
            session_factory=async_session,
            report_progress=_report,
            cmd_id=cmd.id or 0,
        )
    )

    summary = result.summary
    async with async_session() as s:
        repo = MySQLWeChatCommandRepository(s)
        await repo.update_status(
            cmd.id,
            CommandStatus.COMPLETED,
            result_summary=summary,
            progress=f"{result.succeeded}/{result.succeeded + len(result.failed_items)}",
        )
        await s.commit()

    if result.failed_items:
        fails = "；".join(f"{i.get('code', '?')}:{i.get('reason', '?')}" for i in result.failed_items[:10])
        summary = f"{summary}\n部分失败：{fails}"

    push = await reply.send_final(summary)
    async with async_session() as s:
        repo = MySQLWeChatCommandRepository(s)
        try:
            await repo.mark_pushed(cmd.id, push)
            await s.commit()
        except Exception:  # noqa: BLE001
            await s.rollback()


async def _finalize_failed(
    cmd: WeChatCommand, tool: WeChatTool, reply: ReplyChannel, reason: str
) -> None:
    """终态失败：落库 + 推 FAIL（FR-013 禁止静默失败）。"""
    async with async_session() as s:
        repo = MySQLWeChatCommandRepository(s)
        try:
            await repo.update_status(cmd.id, CommandStatus.FAILED, error_message=reason)
            await s.commit()
        except Exception:  # noqa: BLE001
            await s.rollback()
    push = await reply.send_final(f"任务失败：{reason[:1000]}")
    async with async_session() as s:
        repo = MySQLWeChatCommandRepository(s)
        try:
            await repo.mark_pushed(cmd.id, push)
            await s.commit()
        except Exception:  # noqa: BLE001
            await s.rollback()
