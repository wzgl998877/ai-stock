"""微信指令助手域模型 — 对标 ``t_wechat_command``。

一条微信指令的完整生命周期记录（specs/010 data-model.md §1）：

- ``msg_id`` 取 iLink 入站消息 ``client_id``，唯一索引兜底去重（research D3）；
- 状态机 ``pending → running → completed|failed``，另有 ``pending → closed``
  （未识别/未授权，仅留痕）；非法迁移由 Repository 拒绝，防竞态双写。
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class CommandStatus(str, Enum):
    PENDING = "pending"        # 已受理未分发
    RUNNING = "running"        # 慢指令后台执行中
    COMPLETED = "completed"    # 终态：成功
    FAILED = "failed"          # 终态：失败（error_message 必填）
    CLOSED = "closed"          # 未识别/未授权，仅留痕不执行


class PushStatus(str, Enum):
    PENDING = "pending"        # 终态待推送
    PUSHED = "pushed"          # 常规推送受理成功
    DEGRADED = "degraded"      # tokenless 降级推送（context_token 过期）
    FAILED = "failed"          # 推送失败（结果仍可查询兜底）


# 合法状态迁移表（data-model.md §1 状态机）
_VALID_TRANSITIONS: dict[CommandStatus, frozenset[CommandStatus]] = {
    CommandStatus.PENDING: frozenset(
        {CommandStatus.RUNNING, CommandStatus.COMPLETED, CommandStatus.FAILED, CommandStatus.CLOSED}
    ),
    CommandStatus.RUNNING: frozenset({CommandStatus.COMPLETED, CommandStatus.FAILED}),
    # 终态不可再迁移
    CommandStatus.COMPLETED: frozenset(),
    CommandStatus.FAILED: frozenset(),
    CommandStatus.CLOSED: frozenset(),
}


def is_valid_transition(src: CommandStatus, dst: CommandStatus) -> bool:
    """状态机守卫：非法迁移返回 False（Repository 据此拒绝更新）。"""
    return dst in _VALID_TRANSITIONS.get(src, frozenset())


@dataclass
class WeChatCommand:
    """一条微信指令的全生命周期记录。"""

    msg_id: str                          # iLink client_id（幂等去重键）
    user_id: str                         # 发送者 from_user_id
    raw_text: str                        # 用户原文
    tool_name: Optional[str] = None      # 解析出的工具名；None=未识别
    params: Optional[dict] = None        # 解析出的参数
    status: CommandStatus = CommandStatus.PENDING
    progress: Optional[str] = None       # 人类可读进度（"3/10"）
    result_summary: Optional[str] = None # 终态摘要（推送原文）
    push_status: Optional[PushStatus] = None
    error_message: Optional[str] = None  # 失败原因（failed 必填）
    id: Optional[int] = None
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None
