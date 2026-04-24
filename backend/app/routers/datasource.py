"""Data source configuration API router.

Provides:
- GET    /api/v1/datasources         — List all datasource configs (api_key masked)
- POST   /api/v1/datasources         — Create/update a datasource config
- PUT    /api/v1/datasources/{type}  — Update a datasource config
- DELETE /api/v1/datasources/{type}  — Delete a datasource config
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.domain.models.stock_data import SourceType, DataSourceConfig
from app.domain.repositories.datasource_repo import DataSourceRepository
from app.infrastructure.repositories.mysql_datasource_repo import MySQLDataSourceRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/datasources", tags=["datasources"])


def _get_repo(db: AsyncSession = Depends(get_db)) -> DataSourceRepository:
    return MySQLDataSourceRepository(db)


# --- Pydantic DTOs ---

class DataSourceConfigRequest(BaseModel):
    source_type: str
    api_key: Optional[str] = None
    is_enabled: bool = True
    priority: int = 99


class DataSourceConfigResponse(BaseModel):
    source_type: str
    api_key_masked: Optional[str] = None
    is_enabled: bool
    priority: int
    has_configured: bool


def _to_response(config: DataSourceConfig) -> DataSourceConfigResponse:
    masked = None
    if config.api_key:
        # Decrypt for masking
        key_display = config.api_key[:8] + "..." + config.api_key[-4:] if len(config.api_key) > 12 else "***"
        masked = key_display
    return DataSourceConfigResponse(
        source_type=config.source_type.value if hasattr(config.source_type, "value") else str(config.source_type),
        api_key_masked=masked,
        is_enabled=config.is_enabled,
        priority=config.priority,
        has_configured=config.is_configured(),
    )


@router.get("")
async def list_datasources(repo: DataSourceRepository = Depends(_get_repo)):
    """List all datasource configurations with masked api_keys."""
    configs = await repo.get_all()
    return {"data": [_to_response(c) for c in configs]}


@router.post("", status_code=201)
async def create_datasource(
    req: DataSourceConfigRequest,
    repo: DataSourceRepository = Depends(_get_repo),
):
    """Create or update a datasource configuration."""
    try:
        src_type = SourceType(req.source_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"无效的数据源类型: {req.source_type}")

    config = DataSourceConfig(
        source_type=src_type,
        api_key=req.api_key,
        is_enabled=req.is_enabled,
        priority=req.priority,
    )

    saved = await repo.save(config)
    return {"data": _to_response(saved)}


@router.put("/{source_type}")
async def update_datasource(
    source_type: str,
    req: DataSourceConfigRequest,
    repo: DataSourceRepository = Depends(_get_repo),
):
    """Update a datasource configuration."""
    try:
        src_type = SourceType(source_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"无效的数据源类型: {source_type}")

    update_fields = {
        "is_enabled": req.is_enabled,
        "priority": req.priority,
    }
    if req.api_key:
        update_fields["api_key"] = req.api_key

    try:
        updated = await repo.update(src_type, **update_fields)
        return {"data": _to_response(updated)}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{source_type}", status_code=204)
async def delete_datasource(
    source_type: str,
    repo: DataSourceRepository = Depends(_get_repo),
):
    """Delete a datasource configuration."""
    try:
        src_type = SourceType(source_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"无效的数据源类型: {source_type}")

    deleted = await repo.delete(src_type)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"数据源 {source_type} 未找到")
