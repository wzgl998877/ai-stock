"""Tavily 搜索 Provider — 复用 tavily-python SDK + asyncio.to_thread 异步包装"""

import asyncio
import logging
from typing import Any, List

from app.domain.value_objects.search_result import SearchResult, SearchResponse
from app.infrastructure.search.base_provider import BaseSearchProvider

logger = logging.getLogger(__name__)


class TavilySearchProvider(BaseSearchProvider):
    """Tavily 搜索 — SDK 同步调用包装为异步。"""

    def __init__(self, api_keys: List[str]):
        super().__init__(api_keys, "Tavily")

    async def _do_search(
        self,
        query: str,
        max_results: int,
        days: int,
        api_key: str,
        **kwargs: Any,
    ) -> SearchResponse:
        try:
            from tavily import TavilyClient
        except ImportError:
            return SearchResponse(
                query=query, provider=self._name, success=False,
                error_message="tavily-python 未安装",
            )

        topic = kwargs.get("topic", "news")

        def _sync_call() -> dict:
            client = TavilyClient(api_key=api_key)
            return client.search(
                query,
                max_results=max_results,
                search_depth="advanced",
                topic=topic,
                days=days,
            )

        try:
            response = await asyncio.to_thread(_sync_call)
        except Exception as e:
            return SearchResponse(
                query=query, provider=self._name, success=False,
                error_message=str(e),
            )

        items = response.get("results", [])
        results: List[SearchResult] = []
        for item in items[:max_results]:
            results.append(SearchResult(
                title=item.get("title", ""),
                snippet=item.get("content", ""),
                url=item.get("url", ""),
                source=self._extract_domain(item.get("url", "")),
                published_date=item.get("published_date"),
            ))

        return SearchResponse(
            query=query, results=results, provider=self._name, success=True,
        )
