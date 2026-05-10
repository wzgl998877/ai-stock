"""Anspire 搜索 Provider — GET https://plugin.anspire.cn/api/ntsearch/search"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, List

import httpx

from app.domain.value_objects.search_result import SearchResult, SearchResponse
from app.infrastructure.search.base_provider import BaseSearchProvider

logger = logging.getLogger(__name__)


class AnspireSearchProvider(BaseSearchProvider):
    """Anspire 搜索 — 轻量级，适合辅助搜索。"""

    API_URL = "https://plugin.anspire.cn/api/ntsearch/search"

    def __init__(self, api_keys: List[str]):
        super().__init__(api_keys, "Anspire")

    async def _do_search(
        self,
        query: str,
        max_results: int,
        days: int,
        api_key: str,
        **kwargs: Any,
    ) -> SearchResponse:
        now = datetime.now()
        from_time = now - timedelta(days=days)
        params = {
            "query": query,
            "top_k": max_results,
            "FromTime": from_time.strftime("%Y-%m-%d %H:%M:%S"),
            "ToTime": now.strftime("%Y-%m-%d %H:%M:%S"),
        }
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}

        last_exc: Exception | None = None
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.get(self.API_URL, params=params, headers=headers)
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
        items = data.get("data", {}).get("results", [])

        results: List[SearchResult] = []
        for item in items[:max_results]:
            results.append(SearchResult(
                title=item.get("title", ""),
                snippet=item.get("content", ""),
                url=item.get("url", ""),
                source=self._extract_domain(item.get("url", "")),
                published_date=item.get("date"),
            ))

        return SearchResponse(
            query=query, results=results, provider=self._name, success=True,
        )
