"""博查搜索 Provider — POST https://api.bocha.cn/v1/web-search"""

import asyncio
import logging
from typing import Any, List

import httpx

from app.domain.value_objects.search_result import SearchResult, SearchResponse
from app.infrastructure.search.base_provider import BaseSearchProvider

logger = logging.getLogger(__name__)


class BochaSearchProvider(BaseSearchProvider):
    """博查搜索（Bocha）— 中文搜索优化，支持 AI 摘要。"""

    API_URL = "https://api.bocha.cn/v1/web-search"

    def __init__(self, api_keys: List[str]):
        super().__init__(api_keys, "Bocha")

    @staticmethod
    def _map_freshness(days: int) -> str:
        if days <= 1:
            return "oneDay"
        if days <= 7:
            return "oneWeek"
        return "oneMonth"

    async def _do_search(
        self,
        query: str,
        max_results: int,
        days: int,
        api_key: str,
        **kwargs: Any,
    ) -> SearchResponse:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "query": query,
            "freshness": self._map_freshness(days),
            "summary": True,
            "count": max_results,
        }

        # 手动重试（不引入 tenacity）
        last_exc: Exception | None = None
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.post(self.API_URL, headers=headers, json=payload)
                    resp.raise_for_status()
                break
            except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError) as exc:
                last_exc = exc
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)
                continue
        else:
            return SearchResponse(
                query=query, provider=self._name, success=False,
                error_message=f"请求失败: {last_exc}",
            )

        data = resp.json()
        web_pages = (
            data.get("data", {})
            .get("webPages", {})
            .get("value", [])
        )

        results: List[SearchResult] = []
        for item in web_pages[:max_results]:
            results.append(SearchResult(
                title=item.get("name", ""),
                snippet=item.get("summary") or item.get("snippet", ""),
                url=item.get("url", ""),
                source=self._extract_domain(item.get("url", "")),
                published_date=item.get("datePublished"),
            ))

        return SearchResponse(
            query=query, results=results, provider=self._name, success=True,
        )
