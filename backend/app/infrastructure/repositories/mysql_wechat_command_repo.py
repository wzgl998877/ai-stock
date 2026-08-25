"""MySQL WeChat Command Repository — 操作 t_wechat_command（specs/010）。

职责（对标 MySQLSyncTaskRepository 惯例：flush 不 commit，由调用方 commit）：

- ``create``：撞 ``uk_wcmd_msg_id`` 唯一索引时抛 ``DuplicateCommandError``，
  网关据此判定重复消息静默跳过（research D3，DB 是去重的硬约束）；
- ``update_status``：状态机守护，非法迁移抛 ``InvalidTransitionError``（防竞态双写）；
- ``fail_orphans``：服务启动时把遗留 running/pending 记录批量标 failed
  （服务重启必然丢任务，不留"永久执行中"僵尸，research D9）。
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import select, func, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.wechat_command import (
    CommandStatus,
    PushStatus,
    WeChatCommand,
    is_valid_transition,
)
from app.infrastructure.db.models import WeChatCommandModel


class DuplicateCommandError(Exception):
    """msg_id 已存在——重复送达的消息，调用方应静默跳过。"""


class InvalidTransitionError(Exception):
    """非法状态迁移（如终态后再更新）——疑似并发双写。"""


def _to_entity(m: WeChatCommandModel) -> WeChatCommand:
    return WeChatCommand(
        id=m.id,
        msg_id=m.msg_id,
        user_id=m.user_id,
        raw_text=m.raw_text,
        tool_name=m.tool_name,
        params=m.params_json,
        status=CommandStatus(m.status),
        progress=m.progress,
        result_summary=m.result_summary,
        push_status=PushStatus(m.push_status) if m.push_status else None,
        error_message=m.error_message,
        create_time=m.create_time,
        update_time=m.update_time,
    )


class MySQLWeChatCommandRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, cmd: WeChatCommand) -> WeChatCommand:
        """插入受理记录；msg_id 撞唯一索引抛 DuplicateCommandError。"""
        model = WeChatCommandModel(
            msg_id=cmd.msg_id,
            user_id=cmd.user_id,
            raw_text=cmd.raw_text[:512],
            tool_name=cmd.tool_name,
            params_json=cmd.params,
            status=cmd.status.value,
            create_time=datetime.now(),
            update_time=datetime.now(),
        )
        self.session.add(model)
        try:
            await self.session.flush()
        except IntegrityError as e:
            await self.session.rollback()
            raise DuplicateCommandError(f"msg_id 重复: {cmd.msg_id}") from e
        cmd.id = model.id
        cmd.create_time = model.create_time
        return cmd

    async def get_by_msg_id(self, msg_id: str) -> Optional[WeChatCommand]:
        stmt = select(WeChatCommandModel).where(WeChatCommandModel.msg_id == msg_id)
        model = (await self.session.execute(stmt)).scalar_one_or_none()
        return _to_entity(model) if model else None

    async def update_status(
        self,
        cmd_id: int,
        status: CommandStatus,
        *,
        tool_name: Optional[str] = None,
        params: Optional[dict] = None,
        progress: Optional[str] = None,
        result_summary: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> WeChatCommand:
        """状态机守护更新；仅覆盖显式传入的字段。"""
        model = await self.session.get(WeChatCommandModel, cmd_id)
        if not model:
            raise ValueError(f"WeChatCommand not found: {cmd_id}")
        old = CommandStatus(model.status)
        if old != status and not is_valid_transition(old, status):
            raise InvalidTransitionError(f"非法状态迁移: {old.value} → {status.value} (id={cmd_id})")
        model.status = status.value
        if tool_name is not None:
            model.tool_name = tool_name
        if params is not None:
            model.params_json = params
        if progress is not None:
            model.progress = progress[:64]
        if result_summary is not None:
            model.result_summary = result_summary
        if error_message is not None:
            model.error_message = error_message[:1024]
        model.update_time = datetime.now()
        await self.session.flush()
        return _to_entity(model)

    async def mark_pushed(self, cmd_id: int, push_status: PushStatus) -> None:
        """终态推送结果回写（pushed/degraded/failed）。"""
        model = await self.session.get(WeChatCommandModel, cmd_id)
        if not model:
            raise ValueError(f"WeChatCommand not found: {cmd_id}")
        model.push_status = push_status.value
        model.update_time = datetime.now()
        await self.session.flush()

    async def update_progress(self, cmd_id: int, progress: str) -> None:
        """执行中进度回写（"3/10"）。"""
        model = await self.session.get(WeChatCommandModel, cmd_id)
        if not model:
            return
        model.progress = progress[:64]
        model.update_time = datetime.now()
        await self.session.flush()

    async def find_running(
        self, user_id: Optional[str] = None, exclude_id: Optional[int] = None
    ) -> list[WeChatCommand]:
        """当前执行中的慢指令（单飞 BUSY / 进度查询用）。

        ``exclude_id``：调用方自身指令 id（快指令执行时自身体态是 pending，
        不排除会查到自己 → "正在执行 None"误报）。
        """
        stmt = select(WeChatCommandModel).where(
            WeChatCommandModel.status.in_(
                [CommandStatus.PENDING.value, CommandStatus.RUNNING.value]
            )
        )
        if user_id:
            stmt = stmt.where(WeChatCommandModel.user_id == user_id)
        if exclude_id:
            stmt = stmt.where(WeChatCommandModel.id != exclude_id)
        stmt = stmt.order_by(WeChatCommandModel.id.desc())
        models = (await self.session.execute(stmt)).scalars().all()
        return [_to_entity(m) for m in models]

    async def recent_for_user(
        self, user_id: str, limit: int = 10, include_closed: bool = False
    ) -> list[WeChatCommand]:
        """某用户最近的指令记录（执行记录指令用）。"""
        stmt = select(WeChatCommandModel).where(WeChatCommandModel.user_id == user_id)
        if not include_closed:
            stmt = stmt.where(WeChatCommandModel.status != CommandStatus.CLOSED.value)
        stmt = stmt.order_by(WeChatCommandModel.id.desc()).limit(limit)
        models = (await self.session.execute(stmt)).scalars().all()
        return [_to_entity(m) for m in models]

    async def fail_orphans(self, reason: str = "服务重启中断") -> int:
        """启动扫尾：遗留 pending/running → failed（含原因），返回清理条数。"""
        result = await self.session.execute(
            update(WeChatCommandModel)
            .where(
                WeChatCommandModel.status.in_(
                    [CommandStatus.PENDING.value, CommandStatus.RUNNING.value]
                )
            )
            .values(
                status=CommandStatus.FAILED.value,
                error_message=reason,
                update_time=datetime.now(),
            )
        )
        await self.session.flush()
        return result.rowcount or 0

    async def count_all(self) -> int:
        return (await self.session.execute(select(func.count()).select_from(WeChatCommandModel))).scalar() or 0
