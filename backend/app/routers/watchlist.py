"""自选股路由"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user
from app.infrastructure.repositories.mysql_watchlist_repo import MySQLWatchlistRepository
from app.application.use_cases.watchlist import WatchlistUseCase

router = APIRouter(prefix="/api/v1/watchlist", tags=["watchlist"])


def _get_use_case(db: AsyncSession = Depends(get_db)) -> tuple[WatchlistUseCase, AsyncSession]:
    repo = MySQLWatchlistRepository(db)
    return WatchlistUseCase(repo), db


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
    if not stock_code:
        raise HTTPException(status_code=400, detail="stock_code 不能为空")
    item = await uc.add_stock(current_user.user_id, group_id, stock_code, stock_name)
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
