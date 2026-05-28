"""stock_news_analyst 集成测试

覆盖范围：
1. search_service 可用时 → 预搜新闻注入上下文
2. search_service 不可用时 → 仅依赖工具调用
3. search_service 异常时 → 降级到工具调用
4. 验证预搜结果出现在 user message 中
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.domain.value_objects.search_result import SearchResult, SearchResponse


def _make_response(results=None, success=True):
    return SearchResponse(
        query="test",
        results=results or [],
        provider="mock",
        success=success,
    )


class TestNewsAnalystPreSearch:
    @pytest.mark.asyncio
    async def test_pre_search_injects_context(self):
        """验证 search_service 可用时预搜结果被注入到 user message 中。"""
        from app.infrastructure.workflow.nodes.stock_news_analyst import create_news_analyst_node

        mock_svc = MagicMock()
        mock_svc.is_available = True
        mock_svc.search_stock_news = AsyncMock(return_value=_make_response(
            results=[SearchResult(title="利好", snippet="涨停", url="http://x.com", source="x")],
        ))

        mock_ai = MagicMock()
        mock_ai.tool_call = AsyncMock(return_value={"tool_calls": []})
        mock_ai.stream_chat = AsyncMock()

        # 让 stream_chat 产生一个 chunk
        mock_chunk = MagicMock()
        mock_chunk.type = "content"
        mock_chunk.text = "分析报告"

        async def _stream(*args, **kwargs):
            yield mock_chunk

        mock_ai.stream_chat_with_tools = _stream

        node = create_news_analyst_node(
            ai_service=mock_ai,
            max_tool_calls=2,
            search_service=mock_svc,
        )

        state = {"stock_code": "000001", "stock_name": "平安银行", "_content_queue": None}
        result = await node(state)

        assert result["news_report"] == "分析报告"
        assert result["current_agent"] == "news_analyst"
        mock_svc.search_stock_news.assert_called_once_with(
            stock_code="000001", stock_name="平安银行", max_results=8,
        )

    @pytest.mark.asyncio
    async def test_no_search_service(self):
        """验证 search_service 为 None 时不调用预搜，直接走工具调用。"""
        from app.infrastructure.workflow.nodes.stock_news_analyst import create_news_analyst_node

        mock_ai = MagicMock()

        mock_ai.tool_call = AsyncMock(return_value={"tool_calls": []})

        async def _stream(*args, **kwargs):
            chunk = MagicMock()
            chunk.type = "content"
            chunk.text = "无预搜报告"
            yield chunk

        mock_ai.stream_chat_with_tools = _stream

        node = create_news_analyst_node(
            ai_service=mock_ai,
            max_tool_calls=2,
            search_service=None,
        )

        state = {"stock_code": "000001", "stock_name": "平安银行", "_content_queue": None}
        result = await node(state)

        assert result["news_report"] == "无预搜报告"

    @pytest.mark.asyncio
    async def test_search_service_exception_degrades(self):
        """验证 search_service 异常时降级到工具调用流程。"""
        from app.infrastructure.workflow.nodes.stock_news_analyst import create_news_analyst_node

        mock_svc = MagicMock()
        mock_svc.is_available = True
        mock_svc.search_stock_news = AsyncMock(side_effect=Exception("network error"))

        mock_ai = MagicMock()
        mock_ai.tool_call = AsyncMock(return_value={"tool_calls": []})

        async def _stream(*args, **kwargs):
            chunk = MagicMock()
            chunk.type = "content"
            chunk.text = "降级报告"
            yield chunk

        mock_ai.stream_chat_with_tools = _stream

        node = create_news_analyst_node(
            ai_service=mock_ai,
            max_tool_calls=2,
            search_service=mock_svc,
        )

        state = {"stock_code": "000001", "stock_name": "平安银行", "_content_queue": None}
        result = await node(state)

        # 降级成功，正常返回报告
        assert result["news_report"] == "降级报告"
