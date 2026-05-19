"""retrieve 节点向量检索单元测试"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from app.infrastructure.workflow.nodes.retrieve import create_retrieve_node
from app.domain.entities.vector_search import VectorSearchResult


def _make_state(raw_text="国际油价突破 85 美元", user_id="default"):
    return {"raw_text": raw_text, "user_id": user_id}


class TestRetrieveNodeVector:
    """retrieve 节点向量检索单元测试"""

    @pytest.mark.asyncio
    async def test_vector_search_returns_results(self):
        """向量检索有结果时返回向量结果"""
        mock_embedding_svc = MagicMock()
        mock_embedding_svc.is_ready.return_value = True
        mock_embedding_svc.embed = AsyncMock(return_value=[0.1] * 1024)

        mock_vector_repo = MagicMock()
        mock_vector_repo.search = AsyncMock(return_value=[
            VectorSearchResult(
                doc_id="article_1",
                score=0.85,
                metadata={"title": "油价分析", "event_type": "geopolitical"},
                document="关于油价的分析报告",
            ),
        ])

        node = create_retrieve_node(
            session_factory=MagicMock(),
            vector_search_repo=mock_vector_repo,
            embedding_service=mock_embedding_svc,
        )

        result = await node(_make_state())

        assert len(result["search_results"]) == 1
        assert result["search_results"][0]["title"] == "油价分析"
        assert result["search_results"][0]["score"] == 0.85
        mock_embedding_svc.embed.assert_called_once()
        mock_vector_repo.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_vector_search_empty_falls_back_to_fulltext(self):
        """向量检索无结果时回退到 FULLTEXT"""
        mock_embedding_svc = MagicMock()
        mock_embedding_svc.is_ready.return_value = True
        mock_embedding_svc.embed = AsyncMock(return_value=[0.1] * 1024)

        mock_vector_repo = MagicMock()
        mock_vector_repo.search = AsyncMock(return_value=[])

        # Mock session_factory 和 MySQL 搜索
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session_factory = MagicMock(return_value=mock_session)

        mock_article = MagicMock()
        mock_article.title = "历史文章"
        mock_article.summary = "摘要"
        mock_article.content = "内容"
        mock_article.event_type = "policy"
        mock_article.create_time = None

        with patch("app.infrastructure.workflow.nodes.retrieve.MySQLSearchRepository") as MockSearchRepo:
            mock_search_instance = MagicMock()
            mock_search_instance.search = AsyncMock(return_value=([mock_article], 1))
            MockSearchRepo.return_value = mock_search_instance

            node = create_retrieve_node(
                session_factory=mock_session_factory,
                vector_search_repo=mock_vector_repo,
                embedding_service=mock_embedding_svc,
            )

            result = await node(_make_state())

            assert len(result["search_results"]) == 1
            assert result["search_results"][0]["title"] == "历史文章"

    @pytest.mark.asyncio
    async def test_embedding_not_ready_uses_fulltext(self):
        """embedding 服务不可用时直接走 FULLTEXT"""
        mock_embedding_svc = MagicMock()
        mock_embedding_svc.is_ready.return_value = False

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session_factory = MagicMock(return_value=mock_session)

        with patch("app.infrastructure.workflow.nodes.retrieve.MySQLSearchRepository") as MockSearchRepo:
            mock_search_instance = MagicMock()
            mock_search_instance.search = AsyncMock(return_value=([], 0))
            MockSearchRepo.return_value = mock_search_instance

            node = create_retrieve_node(
                session_factory=mock_session_factory,
                vector_search_repo=MagicMock(),
                embedding_service=mock_embedding_svc,
            )

            result = await node(_make_state())

            # FULLTEXT 返回空，但不应抛异常
            assert result["search_results"] == []

    @pytest.mark.asyncio
    async def test_short_text_skips_search(self):
        """输入文本过短时跳过检索"""
        node = create_retrieve_node(session_factory=MagicMock())

        result = await node({"raw_text": "ab", "user_id": "default"})

        assert result["search_results"] == []
        assert "跳过" in result["thinking_done_msg"]

    @pytest.mark.asyncio
    async def test_output_format_compatible(self):
        """输出格式与现有格式兼容"""
        mock_embedding_svc = MagicMock()
        mock_embedding_svc.is_ready.return_value = True
        mock_embedding_svc.embed = AsyncMock(return_value=[0.1] * 1024)

        mock_vector_repo = MagicMock()
        mock_vector_repo.search = AsyncMock(return_value=[
            VectorSearchResult(
                doc_id="article_1",
                score=0.9,
                metadata={"title": "测试", "event_type": "policy"},
                document="测试文档",
            ),
        ])

        node = create_retrieve_node(
            session_factory=MagicMock(),
            vector_search_repo=mock_vector_repo,
            embedding_service=mock_embedding_svc,
        )

        result = await node(_make_state())

        # 验证输出包含必需字段
        item = result["search_results"][0]
        assert "title" in item
        assert "summary" in item
        assert "content" in item
        assert "event_type" in item
        assert "thinking_done_msg" in result
