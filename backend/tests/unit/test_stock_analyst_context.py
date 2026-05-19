"""Agent 上下文注入单元测试 — 验证 RAG 知识库上下文注入到新闻分析师 Agent

覆盖范围：
1. 知识库有相关文章 → 上下文注入到 user message
2. 无相关文章 → 不注入，Agent 行为不变
3. 上下文超过 2000 字 → 截断
4. Embedding 不可用 → Agent 行为不变
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.domain.entities.vector_search import VectorSearchResult


class _FakeAIService:
    """轻量 mock AIService，可捕获 stream_chat 调用参数。"""

    def __init__(self):
        self.tool_call = AsyncMock(return_value={"tool_calls": []})
        self.captured_history = None

    async def tool_call(self, messages, tools, tool_choice, max_tokens):
        return {"tool_calls": []}

    async def stream_chat(self, *, system_prompt, user_message, history_messages,
                          temperature=0.3, max_tokens=4096):
        self.captured_history = history_messages
        chunk = MagicMock()
        chunk.type = "content"
        chunk.text = "新闻分析报告"
        yield chunk


def _make_mock_ai():
    """构建可捕获 stream_chat 参数的 fake AIService。"""
    return _FakeAIService()


def _make_state(stock_code="300750", stock_name="宁德时代"):
    return {
        "stock_code": stock_code,
        "stock_name": stock_name,
        "_content_queue": None,
    }


def _get_user_content(fake_ai):
    """从 captured_history 中提取 user message 的 content。"""
    if fake_ai.captured_history:
        for msg in fake_ai.captured_history:
            if msg.get("role") == "user":
                return msg.get("content", "")
    return ""


class TestStockAnalystContextInjection:
    """Agent 上下文注入单元测试"""

    @pytest.mark.asyncio
    async def test_knowledge_results_injects_context(self):
        """知识库有相关文章时注入上下文到 user message"""
        from app.infrastructure.workflow.nodes.stock_news_analyst import create_news_analyst_node

        mock_embedding_svc = MagicMock()
        mock_embedding_svc.is_ready.return_value = True
        mock_embedding_svc.embed = AsyncMock(return_value=[0.1] * 1024)

        mock_vector_repo = MagicMock()
        mock_vector_repo.search = AsyncMock(return_value=[
            VectorSearchResult(
                doc_id="article_1",
                score=0.85,
                metadata={"title": "宁德时代深度分析"},
                document="宁德时代作为动力电池龙头企业，在新能源领域占据重要地位。",
            ),
            VectorSearchResult(
                doc_id="article_2",
                score=0.78,
                metadata={"title": "锂电池行业研究报告"},
                document="锂电池行业景气度持续上升，龙头公司受益明显。",
            ),
        ])

        fake_ai = _make_mock_ai()

        node = create_news_analyst_node(
            ai_service=fake_ai,
            max_tool_calls=2,
            search_service=None,
            vector_search_repo=mock_vector_repo,
            embedding_service=mock_embedding_svc,
        )

        result = await node(_make_state())

        # 基本返回结构正确
        assert result["news_report"] == "新闻分析报告"
        assert result["current_agent"] == "news_analyst"

        # 验证 embed 被调用（用股票名+分析关键词）
        mock_embedding_svc.embed.assert_called_once()
        call_args = mock_embedding_svc.embed.call_args[0][0]
        assert "宁德时代" in call_args

        # 验证 vector_search 被调用
        mock_vector_repo.search.assert_called_once()
        search_kwargs = mock_vector_repo.search.call_args[1]
        assert search_kwargs["top_k"] == 3
        assert search_kwargs["collection"] == "knowledge_articles"

        # 验证上下文被注入到 user message
        user_content = _get_user_content(fake_ai)
        assert "宁德时代深度分析" in user_content
        assert "知识库中与该股票相关的历史分析摘要" in user_content

    @pytest.mark.asyncio
    async def test_no_knowledge_results_no_injection(self):
        """知识库无相关文章时不注入上下文"""
        from app.infrastructure.workflow.nodes.stock_news_analyst import create_news_analyst_node

        mock_embedding_svc = MagicMock()
        mock_embedding_svc.is_ready.return_value = True
        mock_embedding_svc.embed = AsyncMock(return_value=[0.1] * 1024)

        mock_vector_repo = MagicMock()
        mock_vector_repo.search = AsyncMock(return_value=[])

        fake_ai = _make_mock_ai()

        node = create_news_analyst_node(
            ai_service=fake_ai,
            max_tool_calls=2,
            search_service=None,
            vector_search_repo=mock_vector_repo,
            embedding_service=mock_embedding_svc,
        )

        result = await node(_make_state())

        assert result["news_report"] == "新闻分析报告"

        # 验证 user message 中不包含知识库上下文
        user_content = _get_user_content(fake_ai)
        assert "知识库中与该股票相关的历史分析摘要" not in user_content

    @pytest.mark.asyncio
    async def test_context_truncated_at_max_length(self):
        """上下文超过 2000 字时截断"""
        from app.infrastructure.workflow.nodes.stock_news_analyst import create_news_analyst_node

        # 构造超长文档
        long_document = "这是一段很长的分析内容。" * 500  # 约 5000 字

        mock_embedding_svc = MagicMock()
        mock_embedding_svc.is_ready.return_value = True
        mock_embedding_svc.embed = AsyncMock(return_value=[0.1] * 1024)

        mock_vector_repo = MagicMock()
        mock_vector_repo.search = AsyncMock(return_value=[
            VectorSearchResult(
                doc_id="article_1",
                score=0.9,
                metadata={"title": "超长分析报告"},
                document=long_document,
            ),
        ])

        fake_ai = _make_mock_ai()

        with patch("app.core.config.settings") as mock_settings:
            mock_settings.rag_similarity_threshold = 0.7
            mock_settings.rag_max_context_length = 2000

            node = create_news_analyst_node(
                ai_service=fake_ai,
                max_tool_calls=2,
                search_service=None,
                vector_search_repo=mock_vector_repo,
                embedding_service=mock_embedding_svc,
            )

            result = await node(_make_state())

        assert result["news_report"] == "新闻分析报告"

        # 验证上下文被注入但长度不超过限制
        user_content = _get_user_content(fake_ai)
        assert "知识库中与该股票相关的历史分析摘要" in user_content

        # 提取知识库上下文部分，验证截断
        marker = "知识库中与该股票相关的历史分析摘要"
        context_start = user_content.find(marker)
        context_section = user_content[context_start:]
        # 模板标签本身约 200 字 + 截断后的内容 <= ~2200 字
        assert len(context_section) < 3000

    @pytest.mark.asyncio
    async def test_embedding_not_ready_no_injection(self):
        """Embedding 不可用时 Agent 行为不变"""
        from app.infrastructure.workflow.nodes.stock_news_analyst import create_news_analyst_node

        mock_embedding_svc = MagicMock()
        mock_embedding_svc.is_ready.return_value = False

        mock_vector_repo = MagicMock()
        mock_vector_repo.search = AsyncMock(side_effect=AssertionError("不应调用 search"))

        fake_ai = _make_mock_ai()

        node = create_news_analyst_node(
            ai_service=fake_ai,
            max_tool_calls=2,
            search_service=None,
            vector_search_repo=mock_vector_repo,
            embedding_service=mock_embedding_svc,
        )

        result = await node(_make_state())

        assert result["news_report"] == "新闻分析报告"

        # 验证 embed 和 search 都未被调用
        mock_embedding_svc.embed.assert_not_called()
        mock_vector_repo.search.assert_not_called()

        # 验证 user message 中不包含知识库上下文
        user_content = _get_user_content(fake_ai)
        assert "知识库中与该股票相关的历史分析摘要" not in user_content

    @pytest.mark.asyncio
    async def test_vector_search_repo_none_no_injection(self):
        """vector_search_repo 为 None 时不注入"""
        from app.infrastructure.workflow.nodes.stock_news_analyst import create_news_analyst_node

        mock_embedding_svc = MagicMock()
        mock_embedding_svc.is_ready.return_value = True

        fake_ai = _make_mock_ai()

        node = create_news_analyst_node(
            ai_service=fake_ai,
            max_tool_calls=2,
            search_service=None,
            vector_search_repo=None,
            embedding_service=mock_embedding_svc,
        )

        result = await node(_make_state())

        assert result["news_report"] == "新闻分析报告"

        # embed 不应被调用（因为缺少 vector_search_repo）
        mock_embedding_svc.embed.assert_not_called()

    @pytest.mark.asyncio
    async def test_embedding_exception_degrades_gracefully(self):
        """Embedding 异常时优雅降级"""
        from app.infrastructure.workflow.nodes.stock_news_analyst import create_news_analyst_node

        mock_embedding_svc = MagicMock()
        mock_embedding_svc.is_ready.return_value = True
        mock_embedding_svc.embed = AsyncMock(side_effect=Exception("模型加载失败"))

        mock_vector_repo = MagicMock()

        fake_ai = _make_mock_ai()

        node = create_news_analyst_node(
            ai_service=fake_ai,
            max_tool_calls=2,
            search_service=None,
            vector_search_repo=mock_vector_repo,
            embedding_service=mock_embedding_svc,
        )

        result = await node(_make_state())

        # 降级后仍正常返回
        assert result["news_report"] == "新闻分析报告"

        # user message 中不包含知识库上下文
        user_content = _get_user_content(fake_ai)
        assert "知识库中与该股票相关的历史分析摘要" not in user_content
