"""行业数据路由"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.infrastructure.repositories.mysql_industry_repo import MySQLIndustryRepository
from app.application.use_cases.industry import IndustryUseCase

router = APIRouter(prefix="/api/v1/industries", tags=["industry"])


def _get_use_case(db: AsyncSession = Depends(get_db)) -> IndustryUseCase:
    industry_repo = MySQLIndustryRepository(db)
    return IndustryUseCase(industry_repo)


@router.get("")
async def get_industries(uc: IndustryUseCase = Depends(_get_use_case)):
    industries = await uc.list_level1_industries()
    items = [
        {
            "code": ind.industry_code,
            "name": ind.name,
            "display_order": ind.display_order,
        }
        for ind in industries
    ]
    return {"data": {"total": len(items), "items": items}}


@router.get("/{industry_code}/stocks")
async def get_industry_stocks(
    industry_code: str,
    sort_by: str = "change_pct",
    sort_order: str = "desc",
    page: int = 1,
    page_size: int = 20,
    uc: IndustryUseCase = Depends(_get_use_case),
):
    overview = await uc.get_industry_overview(industry_code)
    if not overview:
        return {"data": {"industry": None, "items": [], "total": 0}}

    items = [
        {
            "code": s.stock_code,
            "name": s.name,
            "industry": s.industry,
        }
        for s in overview.top_stocks
    ]

    return {
        "data": {
            "industry": {
                "code": overview.industry_code,
                "name": overview.industry_name,
                "avg_change_pct": 0,
            },
            "items": items,
            "total": overview.stock_count,
        }
    }
