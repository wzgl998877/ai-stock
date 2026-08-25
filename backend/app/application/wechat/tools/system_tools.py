"""系统查询指令工具（specs/010 US2）：执行记录（纯规则保底，永不依赖 LLM）。"""

from __future__ import annotations

from app.application.wechat.tools.base import ToolContext, ToolResult, WeChatTool

_STATUS_LABELS = {
    "pending": "待执行",
    "running": "执行中",
    "completed": "已完成",
    "failed": "失败",
    "closed": "未执行",
}
_PUSH_LABELS = {
    "pending": "待推送",
    "pushed": "已推送",
    "degraded": "降级推送",
    "failed": "推送失败",
}


class CmdHistoryTool(WeChatTool):
    """执行记录查询（US2）。"""

    name = "cmd_history"
    domain = "system"
    description = "查询最近执行的微信指令及其状态（含推送状态）。示例：「执行记录」"
    parameters = {}
    kind = "fast"
    lock_key = None
    risk = "read_only"
    usage = "执行记录"
    patterns = [r"^(?:执行记录|指令记录)$"]

    async def execute(self, ctx: ToolContext) -> ToolResult:
        from app.infrastructure.repositories.mysql_wechat_command_repo import (
            MySQLWeChatCommandRepository,
        )

        async with ctx.session_factory() as s:
            repo = MySQLWeChatCommandRepository(s)
            records = await repo.recent_for_user(ctx.user_id, limit=10, include_closed=True)

        if not records:
            return ToolResult(summary="还没有执行记录。发「跑缠论」试试，或发「帮助」看全部指令。")

        lines = ["最近 10 条指令："]
        for r in records:
            time_str = r.create_time.strftime("%m-%d %H:%M") if r.create_time else "?"
            status = _STATUS_LABELS.get(r.status.value, r.status.value)
            push = _PUSH_LABELS.get(r.push_status.value, "-") if r.push_status else "-"
            text = r.raw_text[:16] + ("…" if len(r.raw_text) > 16 else "")
            lines.append(f"· {time_str} 「{text}」{status}｜{push}")
        return ToolResult(summary="\n".join(lines), succeeded=len(records))
