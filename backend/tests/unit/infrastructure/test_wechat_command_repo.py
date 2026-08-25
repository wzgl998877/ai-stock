"""WeChatCommandRepository 测试（specs/010 T002）：内存 SQLite 真跑 SQL。

覆盖三组核心行为（data-model.md §1）：
1. msg_id 唯一索引兜底去重（DuplicateCommandError）；
2. 状态机守护：非法迁移抛 InvalidTransitionError（防竞态双写）；
3. fail_orphans 孤儿清理：遗留 pending/running → failed（服务重启扫尾）。
"""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.domain.models.wechat_command import CommandStatus, WeChatCommand
from app.infrastructure.db.models import WeChatCommandModel
from app.infrastructure.repositories.mysql_wechat_command_repo import (
    DuplicateCommandError,
    InvalidTransitionError,
    MySQLWeChatCommandRepository,
)

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(WeChatCommandModel.__table__.create)
    maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as s:
        yield s
    await engine.dispose()


def _cmd(msg_id: str = "m1", **kw) -> WeChatCommand:
    base = dict(msg_id=msg_id, user_id="u@im.wechat", raw_text="跑缠论")
    base.update(kw)
    return WeChatCommand(**base)


async def test_create_then_duplicate_raises(session):
    repo = MySQLWeChatCommandRepository(session)
    cmd = await repo.create(_cmd("dup-1"))
    await session.commit()
    assert cmd.id is not None and cmd.status == CommandStatus.PENDING

    with pytest.raises(DuplicateCommandError):
        await repo.create(_cmd("dup-1"))  # 同 msg_id 重放 → 重复信号


async def test_state_machine_guards(session):
    repo = MySQLWeChatCommandRepository(session)
    cmd = await repo.create(_cmd("m2"))
    await session.commit()

    # 合法：pending → running → completed
    await repo.update_status(cmd.id, CommandStatus.RUNNING, tool_name="run_chanlun")
    await repo.update_status(cmd.id, CommandStatus.COMPLETED, result_summary="ok")
    await session.commit()

    # 非法：终态 completed → running（防竞态双写）
    with pytest.raises(InvalidTransitionError):
        await repo.update_status(cmd.id, CommandStatus.RUNNING)


async def test_fail_orphans_cleans_pending_and_running(session):
    repo = MySQLWeChatCommandRepository(session)
    a = await repo.create(_cmd("a"))                      # pending
    b = await repo.create(_cmd("b"))                      # → running
    c = await repo.create(_cmd("c"))                      # → completed（不应被清理）
    await repo.update_status(b.id, CommandStatus.RUNNING)
    await repo.update_status(c.id, CommandStatus.COMPLETED, result_summary="done")
    await session.commit()

    cleaned = await repo.fail_orphans(reason="服务重启中断")
    await session.commit()

    assert cleaned == 2
    ra = await repo.get_by_msg_id("a")
    rb = await repo.get_by_msg_id("b")
    rc = await repo.get_by_msg_id("c")
    assert ra.status == CommandStatus.FAILED and ra.error_message == "服务重启中断"
    assert rb.status == CommandStatus.FAILED
    assert rc.status == CommandStatus.COMPLETED  # 终态不受影响


async def test_recent_for_user_orders_desc(session):
    repo = MySQLWeChatCommandRepository(session)
    for i in range(4):
        await repo.create(_cmd(f"m{i}", raw_text=f"指令{i}"))
    await session.commit()

    records = await repo.recent_for_user("u@im.wechat", limit=3)
    assert len(records) == 3
    assert records[0].raw_text == "指令3"  # 最新在前


async def test_find_running_excludes_self(session):
    """快指令执行中自身体态是 pending：exclude_id 必须把"自己"排除掉。

    场景来源：chanlun_status 查进度时把自己（pending、tool_name 未回写）
    查出来，回了「正在执行 None，稍等片刻。」
    """
    repo = MySQLWeChatCommandRepository(session)
    me = await repo.create(_cmd("me"))                      # 自己：pending（工具名未回写）
    other = await repo.create(_cmd("other"))                # 别的慢任务：running
    await repo.update_status(other.id, CommandStatus.RUNNING, tool_name="run_chanlun")
    await session.commit()

    # 不排除 → 查到自己（旧行为，bug 现场）
    assert [c.id for c in await repo.find_running(user_id="u@im.wechat")] == [other.id, me.id]
    # 排除自己 → 只剩真正在跑的任务
    assert [c.id for c in await repo.find_running(user_id="u@im.wechat", exclude_id=me.id)] == [other.id]
