"""Repository interface for sync task management."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, List
from app.domain.models.stock_data import SyncTask, SourceType, DataType, SyncStatus


class SyncTaskRepository(ABC):
    @abstractmethod
    async def create(self, task: SyncTask) -> SyncTask:
        """创建同步任务记录"""
        ...

    @abstractmethod
    async def get_by_id(self, task_id: str) -> Optional[SyncTask]:
        """根据 task_id 获取任务"""
        ...

    @abstractmethod
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
        """更新任务状态和进度"""
        ...

    @abstractmethod
    async def get_running_by_source(
        self, source_type: SourceType, data_type: DataType
    ) -> Optional[SyncTask]:
        """获取某数据源+数据类型组合下正在运行的任务"""
        ...

    @abstractmethod
    async def list_tasks(
        self,
        page: int = 1,
        page_size: int = 20,
        source_type: Optional[SourceType] = None,
        status: Optional[SyncStatus] = None,
    ) -> tuple[List[SyncTask], int]:
        """分页查询任务历史，返回 (列表, 总数)"""
        ...

    @abstractmethod
    async def count_running_by_source(
        self, source_type: SourceType, data_type: DataType
    ) -> int:
        """统计某数据源+数据类型组合下 running 状态的任务数"""
        ...
