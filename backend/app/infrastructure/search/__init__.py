"""搜索基础设施 — 工厂函数 create_search_service()"""

from typing import List, Optional

from app.core.config import settings
from app.infrastructure.search.base_provider import BaseSearchProvider
from app.infrastructure.search.cache import SearchCache


def _parse_keys(value: str) -> List[str]:
    """解析逗号分隔的 Key 字符串，过滤空值。"""
    return [k.strip() for k in value.split(",") if k.strip()]


def create_search_service():
    """根据配置创建 SearchService 实例，未配置任何 Key 时返回 None。"""
    from app.domain.services.search_service import SearchService

    providers: List[BaseSearchProvider] = []

    # Anspire（最高优先）
    anspire_keys = _parse_keys(settings.anspire_api_keys)
    if anspire_keys:
        from app.infrastructure.search.anspire_provider import AnspireSearchProvider
        providers.append(AnspireSearchProvider(anspire_keys))

    # Bocha
    bocha_keys = _parse_keys(settings.bocha_api_keys)
    if bocha_keys:
        from app.infrastructure.search.bocha_provider import BochaSearchProvider
        providers.append(BochaSearchProvider(bocha_keys))

    # Tavily（兼容现有单 Key + 新增多 Key）
    tavily_keys = _parse_keys(settings.tavily_api_keys)
    if not tavily_keys and settings.tavily_api_key:
        tavily_keys = [settings.tavily_api_key]
    if tavily_keys:
        from app.infrastructure.search.tavily_provider import TavilySearchProvider
        providers.append(TavilySearchProvider(tavily_keys))

    if not providers:
        return None

    cache = SearchCache()
    return SearchService(providers=providers, cache=cache)
