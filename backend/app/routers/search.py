"""搜索 API 端点"""

from fastapi import APIRouter, Request

from app.application.dtos.search_dto import (
    ComprehensiveIntelRequestDTO,
    SearchRequestDTO,
    StockNewsSearchRequestDTO,
)
from app.domain.services.search_service import SearchService

router = APIRouter(prefix="/api/v1/search", tags=["搜索"])


def _get_service(request: Request) -> SearchService | None:
    return getattr(request.app.state, "search_service", None)


@router.post("/news")
async def search_news(request: Request, body: SearchRequestDTO):
    """通用新闻搜索。"""
    service = _get_service(request)
    if not service or not service.is_available:
        return {"success": False, "error": "搜索服务未配置"}
    response = await service.search(body.query, body.max_results, body.days)
    return response.to_dict()


@router.post("/stock-news")
async def search_stock_news(request: Request, body: StockNewsSearchRequestDTO):
    """股票新闻搜索。"""
    service = _get_service(request)
    if not service or not service.is_available:
        return {"success": False, "error": "搜索服务未配置"}
    response = await service.search_stock_news(
        stock_code=body.stock_code,
        stock_name=body.stock_name,
        max_results=body.max_results,
        focus_keywords=body.focus_keywords,
    )
    return response.to_dict()


@router.post("/intel")
async def search_intel(request: Request, body: ComprehensiveIntelRequestDTO):
    """多维度情报搜索。"""
    service = _get_service(request)
    if not service or not service.is_available:
        return {"success": False, "error": "搜索服务未配置"}
    results = await service.search_comprehensive_intel(
        stock_code=body.stock_code,
        stock_name=body.stock_name,
        max_searches=body.max_searches,
    )
    report = SearchService.format_intel_report(results, body.stock_name)
    return {
        "success": True,
        "dimensions": {k: v.to_dict() for k, v in results.items()},
        "report": report,
    }
