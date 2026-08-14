"""自选股路由"""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.sync.sync_executor import _get_lock
from app.application.sync.watchlist_batch_sync import launch_batch_sync
from app.application.use_cases.watchlist import WatchlistUseCase
from app.application.use_cases.watchlist_sync import WatchlistSyncUseCase
from app.core.database import async_session, get_db
from app.core.deps import CurrentUser, get_current_user
from app.domain.models.stock_data import DataType, SourceType, SyncStatus, SyncTask
from app.infrastructure.repositories.mysql_chanlun_repo import MySQLChanlunRepository
from app.infrastructure.repositories.mysql_sync_task_repo import MySQLSyncTaskRepository
from app.infrastructure.repositories.mysql_watchlist_repo import MySQLWatchlistRepository

# watchlist:sync 的全局单飞锁 key
_WATCHLIST_SYNC_LOCK_KEY = "watchlist:sync"

router = APIRouter(prefix="/api/v1/watchlist", tags=["watchlist"])


def _get_use_case(db: AsyncSession = Depends(get_db)) -> tuple[WatchlistUseCase, AsyncSession]:
    repo = MySQLWatchlistRepository(db)
    # 注入缠论仓库：自选股移除时联动清理逐股监控配置（T051）
    chanlun_repo = MySQLChanlunRepository(db)
    return WatchlistUseCase(repo, chanlun_repo=chanlun_repo), db


def _group_to_dict(g) -> dict:
    """将 WatchlistGroup entity 序列化为 dict"""
    return {
        "id": g.id,
        "name": g.name,
        "is_default": g.is_default,
        "display_order": g.display_order,
        "stock_count": getattr(g, "stock_count", 0),
        "stocks": [
            {
                "code": s.stock_code,
                "name": s.stock_name,
                "add_price": getattr(s, "add_price", None),
                "add_time": s.add_time.isoformat() if s.add_time else None,
            }
            for s in getattr(g, "stocks", [])
        ],
    }


@router.get("/groups")
async def get_groups(uc_db: tuple = Depends(_get_use_case), current_user: CurrentUser = Depends(get_current_user)):
    uc, db = uc_db
    groups = await uc.get_groups(current_user.user_id)

    # 填充每个分组内的股票列表
    for g in groups:
        g.stocks = await uc.get_items(current_user.user_id, g.id)

    return {"data": {"groups": [_group_to_dict(g) for g in groups]}}


@router.post("/groups", status_code=201)
async def create_group(
    body: dict,
    uc_db: tuple = Depends(_get_use_case),
    current_user: CurrentUser = Depends(get_current_user),
):
    uc, db = uc_db
    name = body.get("name", "").strip()
    if not name or len(name) > 10:
        raise HTTPException(status_code=400, detail="分组名称须1-10个字符")
    group = await uc.create_group(current_user.user_id, name)
    await db.commit()
    return {"data": _group_to_dict(group)}


@router.put("/groups/{group_id}")
async def rename_group(
    group_id: int,
    body: dict,
    uc_db: tuple = Depends(_get_use_case),
):
    uc, db = uc_db
    name = body.get("name", "").strip()
    if not name or len(name) > 10:
        raise HTTPException(status_code=400, detail="分组名称须1-10个字符")
    group = await uc.update_group(group_id, name=name)
    await db.commit()
    return {"data": _group_to_dict(group)}


@router.delete("/groups/{group_id}")
async def delete_group(
    group_id: int,
    uc_db: tuple = Depends(_get_use_case),
):
    uc, db = uc_db
    await uc.delete_group(group_id)
    await db.commit()
    return {"data": {"message": "分组已删除"}}


@router.post("/groups/{group_id}/stocks", status_code=201)
async def add_stock(
    group_id: int,
    body: dict,
    uc_db: tuple = Depends(_get_use_case),
    current_user: CurrentUser = Depends(get_current_user),
):
    uc, db = uc_db
    stock_code = body.get("stock_code", "").strip()
    stock_name = body.get("stock_name", "").strip()
    add_price = body.get("add_price")
    if not stock_code:
        raise HTTPException(status_code=400, detail="stock_code 不能为空")
    item = await uc.add_stock(current_user.user_id, group_id, stock_code, stock_name, add_price)
    await db.commit()
    return {"data": {"id": item.id, "group_id": item.group_id, "stock_code": item.stock_code, "stock_name": item.stock_name}}


@router.delete("/groups/{group_id}/stocks/{stock_code}", status_code=204)
async def remove_stock(
    group_id: int,
    stock_code: str,
    uc_db: tuple = Depends(_get_use_case),
    current_user: CurrentUser = Depends(get_current_user),
):
    uc, db = uc_db
    await uc.remove_stock(current_user.user_id, group_id, stock_code)
    await db.commit()


@router.post("/sync")
async def sync_watchlist_groups(
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """按自选分组批量同步日K + 30m 行情（异步后台任务）。

    请求体：``{"group_ids": [1, 2, 3]}``，对选中分组内的股票跨分组去重后，
    在后台并发拉取最近 1 年日K（写 ``t_stock_daily_quote``）与 30m（写 ``t_stock_kline_30m``），
    并清除对应 Redis 查询缓存。缠论计算直读 DB，落库即生效。

    端点本身毫秒级返回（仅创建任务记录 + 启动后台 task）；进度可在「数据同步页」
    通过 ``t_sync_task`` 记录查看。同一时刻只允许一个 watchlist 批量同步任务（全局单飞锁）。
    """
    group_ids = body.get("group_ids") or []
    if not isinstance(group_ids, list) or not group_ids:
        raise HTTPException(status_code=400, detail="group_ids 不能为空")

    # 全局单飞：已有 watchlist 批量同步在跑则拒绝
    lock = _get_lock(_WATCHLIST_SYNC_LOCK_KEY)
    if lock.locked():
        raise HTTPException(status_code=409, detail="已有自选股同步任务在执行，请稍后再试")

    # 收集去重股票代码
    wl_repo = MySQLWatchlistRepository(db)
    sync_uc = WatchlistSyncUseCase(wl_repo)
    codes = await sync_uc.collect_unique_codes(current_user.user_id, group_ids)
    if not codes:
        raise HTTPException(status_code=400, detail="所选分组内暂无股票")

    # 创建 t_sync_task 记录并提交（必须提交，否则后台独立 session 看不到）
    task_repo = MySQLSyncTaskRepository(db)
    task = SyncTask(
        task_id=str(uuid.uuid4()),
        source_type=SourceType.SINA,
        data_type=DataType.DAILY_QUOTE,
        status=SyncStatus.PENDING,
        total_count=len(codes),
    )
    task = await task_repo.create(task)
    await db.commit()

    async def _update_cb(
        task_id: str,
        status: str,
        success: int = 0,
        fail: int = 0,
        processed: int = 0,
        error: str | None = None,
    ) -> None:
        """桥接回调：把简短参数映射到 update_status 的真实签名。
        用独立 session 写库；终态（completed/failed）释放锁。"""
        try:
            async with async_session() as s:
                tr = MySQLSyncTaskRepository(s)
                await tr.update_status(
                    task_id,
                    SyncStatus(status),
                    start_time=datetime.now() if status == "running" else None,
                    processed_count=processed,
                    success_count=success,
                    fail_count=fail,
                    error_message=error,
                )
                await s.commit()
        except Exception:
            # 任务记录更新失败不应影响数据已落库的事实
            pass
        finally:
            if status in ("completed", "failed"):
                if lock.locked():
                    lock.release()

    # 获取锁后启动后台任务
    await lock.acquire()
    try:
        launch_batch_sync(task.task_id, codes, async_session, _update_cb)
    except Exception:
        # 启动后台任务本身失败（非后台任务内部异常）：必须释放锁，否则后续同步永远 409
        if lock.locked():
            lock.release()
        # 同步任务记录标记为失败（独立 session，避免污染当前请求 session）
        try:
            async with async_session() as s:
                await MySQLSyncTaskRepository(s).update_status(
                    task.task_id, SyncStatus.FAILED, error_message="启动后台任务失败",
                )
                await s.commit()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail="启动后台同步任务失败")

    return {
        "data": {
            "task_id": task.task_id,
            "total": len(codes),
            "groups": len(group_ids),
            "message": "已开始后台同步",
        }
    }
