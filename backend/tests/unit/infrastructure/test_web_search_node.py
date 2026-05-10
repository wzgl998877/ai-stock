"""web_search_node 单元测试

覆盖范围：
1. search_service 可用时 → 使用统一搜索
2. search_service 不可用时 → 回退旧版 Tavily
3. search_service 异常时 → 回退旧版 Tavily
4. search_service 返回空结果 → 回退旧版 Tavily
5. search_query 为空 → 跳过搜索
6. SearchResponse → dict 格式转换兼容性
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.domain.value_objects.search_result import SearchResult, SearchResponse
from app.infrastructure.workflow.nodes.web_search_node import (
    create_web_search_node,
    _search_response_to_dict_list,
)


def _make_response(results=None, success=True, provider="mock", query="test"):
    return SearchResponse(
        query=query,
        results=results or [],
        provider=provider,
        success=success,
    )


class TestSearchResponseConversion:
    def test_converts_snippet_to_content(self):
        resp = _make_response(results=[
            SearchResult(title="t", snippet="body", url="http://x.com", source="x"),
        ])
        dicts = _search_response_to_dict_list(resp)
        assert len(dicts) == 1
        assert dicts[0]["title"] == "t"
        assert dicts[0]["content"] == "body"
        assert dicts[0]["url"] == "http://x.com"

    def test_empty_results(self):
        resp = _make_response(results=[])
        dicts = _search_response_to_dict_list(resp)
        assert dicts == []


class TestWebSearchNodeWithService:
    @pytest.mark.asyncio
    async def test_uses_search_service_when_available(self):
        mock_svc = MagicMock()
        mock_svc.is_available = True
        mock_svc.search = AsyncMock(return_value=_make_response(
            results=[SearchResult(title="news", snippet="body", url="http://x.com", source="x")],
            provider="Bocha",
        ))

        node = create_web_search_node(search_service=mock_svc)
        result = await node({"search_query": "A股市场"})

        assert len(result["web_search_results"]) == 1
        assert result["web_search_results"][0]["title"] == "news"
        assert result["web_search_results"][0]["content"] == "body"
        assert "找到 1 条结果" in result["thinking_done_msg"]
        mock_svc.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_fallback_when_service_returns_empty(self):
        mock_svc = MagicMock()
        mock_svc.is_available = True
        mock_svc.search = AsyncMock(return_value=_make_response(
            results=[], success=True,
        ))

        node = create_web_search_node(search_service=mock_svc)
        # 服务返回空 → 回退旧版 → 旧版无 Key 返回 []
        result = await node({"search_query": "test"})
        assert isinstance(result["web_search_results"], list)
        assert "thinking_done_msg" in result

    @pytest.mark.asyncio
    async def test_fallback_when_service_raises(self):
        mock_svc = MagicMock()
        mock_svc.is_available = True
        mock_svc.search = AsyncMock(side_effect=Exception("timeout"))

        node = create_web_search_node(search_service=mock_svc)
        # Will try fallback but fail (no tavily key), which is fine
        result = await node({"search_query": "test"})
        assert "web_search_results" in result

    @pytest.mark.asyncio
    async def test_skips_when_query_empty(self):
        node = create_web_search_node(search_service=None)
        result = await node({"search_query": ""})
        assert result["web_search_results"] == []
        assert "跳过" in result["thinking_done_msg"]

    @pytest.mark.asyncio
    async def test_no_service_no_query(self):
        node = create_web_search_node(search_service=None)
        result = await node({"search_query": ""})
        assert result["web_search_results"] == []


class TestWebSearchNodeWithoutService:
    @pytest.mark.asyncio
    async def test_fallback_to_old_search(self):
        node = create_web_search_node(search_service=None)
        # Without tavily key, old search returns []
        result = await node({"search_query": "test"})
        assert isinstance(result["web_search_results"], list)
        assert "thinking_done_msg" in result
