"""MySQL Sync Task Repository — 操作 t_sync_task"""

from datetime import datetime
from typing import Optional, List

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.stock_data import SyncTask, SourceType, DataType, SyncStatus
from app.domain.repositories.sync_task_repo import SyncTaskRepository
from app.infrastructure.db.models import SyncTaskModel


def _to_entity(model: SyncTaskModel) -> SyncTask:
    """ORM model → Domain entity"""
    return SyncTask(
        id=model.id,
        task_id=model.task_id,
        source_type=SourceType(model.source_type),
        data_type=DataType(model.data_type),
        status=SyncStatus(model.status),
        total_count=model.total_count or 0,
        processed_count=model.processed_count or 0,
        success_count=model.success_count or 0,
        fail_count=model.fail_count or 0,
        error_message=model.error_message,
        start_time=model.start_time,
        end_time=model.end_time,
        duration_ms=model.duration_ms,
        create_time=model.create_time,
    )


def _model_from_entity(task: SyncTask) -> SyncTaskModel:
    """Domain entity → ORM model"""
    return SyncTaskModel(
        id=task.id,
        task_id=task.task_id,
        source_type=task.source_type.value,
        data_type=task.data_type.value,
        status=task.status.value,
        total_count=task.total_count if task.total_count else None,
        processed_count=task.processed_count if task.processed_count else None,
        success_count=task.success_count if task.success_count else None,
        fail_count=task.fail_count if task.fail_count else None,
        error_message=task.error_message,
        start_time=task.start_time,
        end_time=task.end_time,
        duration_ms=task.duration_ms,
        create_time=task.create_time or datetime.now(),
    )


class MySQLSyncTaskRepository(SyncTaskRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, task: SyncTask) -> SyncTask:
        model = _model_from_entity(task)
        self.session.add(model)
        await self.session.flush()

        task.id = model.id
        task.create_time = model.create_time
        return task

    async def get_by_id(self, task_id: str) -> Optional[SyncTask]:
        stmt = select(SyncTaskModel).where(SyncTaskModel.task_id == task_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def update_status(
        self,
        task_id: str,
        status: SyncStatus,
        start_time: Optional[datetime] = None,
        processed_count: Optional[int] = None,
        success_count: Optional[int] = None,
        fail_count: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> SyncTask:
        stmt = select(SyncTaskModel).where(SyncTaskModel.task_id == task_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            raise ValueError(f"SyncTask not found: {task_id}")

        model.status = status.value

        if start_time is not None:
            model.start_time = start_time
        if processed_count is not None:
            model.processed_count = processed_count
        if success_count is not None:
            model.success_count = success_count
        if fail_count is not None:
            model.fail_count = fail_count
        if error_message is not None:
            model.error_message = error_message

        # 当状态为 completed 或 failed 时，设置结束时间并计算耗时
        if status in (SyncStatus.COMPLETED, SyncStatus.FAILED):
            model.end_time = datetime.now()
            if model.start_time:
                delta = model.end_time - model.start_time
                model.duration_ms = int(delta.total_seconds() * 1000)

        await self.session.flush()

        # 重新查询以获取最新数据
        stmt = select(SyncTaskModel).where(SyncTaskModel.task_id == task_id)
        result = await self.session.execute(stmt)
        updated = result.scalar_one()
        return _to_entity(updated)

    async def get_running_by_source(
        self, source_type: SourceType, data_type: DataType
    ) -> Optional[SyncTask]:
        stmt = select(SyncTaskModel).where(
            and_(
                SyncTaskModel.source_type == source_type.value,
                SyncTaskModel.data_type == data_type.value,
                SyncTaskModel.status == SyncStatus.RUNNING.value,
            )
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def list_tasks(
        self,
        page: int = 1,
        page_size: int = 20,
        source_type: Optional[SourceType] = None,
        status: Optional[SyncStatus] = None,
    ) -> tuple[List[SyncTask], int]:
        # 构建过滤条件
        conditions = []
        if source_type is not None:
            conditions.append(SyncTaskModel.source_type == source_type.value)
        if status is not None:
            conditions.append(SyncTaskModel.status == status.value)

        where_clause = and_(*conditions) if conditions else True

        # 总数查询
        count_stmt = select(func.count()).select_from(SyncTaskModel).where(where_clause)
        total = (await self.session.execute(count_stmt)).scalar() or 0

        # 数据查询
        stmt = (
            select(SyncTaskModel)
            .where(where_clause)
            .order_by(SyncTaskModel.create_time.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()

        return [_to_entity(m) for m in models], total

    async def count_running_by_source(
        self, source_type: SourceType, data_type: DataType
    ) -> int:
        stmt = select(func.count()).select_from(SyncTaskModel).where(
            and_(
                SyncTaskModel.source_type == source_type.value,
                SyncTaskModel.data_type == data_type.value,
                SyncTaskModel.status == SyncStatus.RUNNING.value,
            )
        )
        return (await self.session.execute(stmt)).scalar() or 0
