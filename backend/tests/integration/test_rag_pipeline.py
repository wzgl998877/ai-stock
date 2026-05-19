"""RAG 端到端集成测试 — 模拟完整语义检索流程"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from app.domain.entities.vector_search import VectorSearchResult


class TestRAGPipeline:
    """RAG 端到端集成测试"""

    @pytest.mark.asyncio
    async def test_article_save_and_retrieve(self):
        """文章保存 → embedding 写入 → retrieve 语义检索"""
        # 1. 保存文章 → 生成 embedding
        mock_article_repo = AsyncMock()
        saved_article = MagicMock()
        saved_article.article_id = "art_001"
        saved_article.title = "新能源补贴政策分析"
        saved_article.summary = "国务院发布新能源补贴政策"
        saved_article.content = "详细内容..."
        saved_article.event_type = "policy"
        saved_article.user_id = "user_001"
        saved_article.stocks = [MagicMock(stock_code="300750")]
        saved_article.industries = [MagicMock(industry_code="new_energy")]
        mock_article_repo.save = AsyncMock(return_value=saved_article)

        mock_industry_repo = AsyncMock()
        mock_industry = MagicMock()
        mock_industry.industry_code = "new_energy"
        mock_industry_repo.find_by_name = AsyncMock(return_value=mock_industry)

        mock_embedding_svc = MagicMock()
        mock_embedding_svc.is_ready.return_value = True
        mock_embedding_svc.embed = AsyncMock(return_value=[0.1] * 1024)

        mock_vector_repo = MagicMock()
        mock_vector_repo.add = AsyncMock()

        from app.application.use_cases.manage_article import SaveArticleUseCase
        uc = SaveArticleUseCase(mock_article_repo, mock_industry_repo, mock_vector_repo, mock_embedding_svc)

        article = await uc.execute(
            title="新能源补贴政策分析",
            summary="国务院发布新能源补贴政策",
            content="详细内容...",
            event_type="policy",
            raw_input="新能源补贴",
            industry_codes=["新能源"],
            stock_refs=[{"code": "300750", "name": "宁德时代"}],
            user_id="user_001",
        )

        # 验证 embedding 写入被调用
        mock_vector_repo.add.assert_called_once()
        call_kwargs = mock_vector_repo.add.call_args[1]
        assert call_kwargs["collection"] == "knowledge_articles"
        assert call_kwargs["doc_id"] == "article_art_001"

        # 2. 模拟 retrieve 语义检索
        mock_vector_repo.search = AsyncMock(return_value=[
            VectorSearchResult(
                doc_id="article_art_001",
                score=0.92,
                metadata={"title": "新能源补贴政策分析", "event_type": "policy"},
                document="新能源补贴政策分析\n国务院发布新能源补贴政策",
            ),
        ])

        from app.infrastructure.workflow.nodes.retrieve import create_retrieve_node
        node = create_retrieve_node(
            session_factory=MagicMock(),
            vector_search_repo=mock_vector_repo,
            embedding_service=mock_embedding_svc,
        )

        result = await node({"raw_text": "新能源补贴政策对光伏行业的影响", "user_id": "user_001"})

        assert len(result["search_results"]) == 1
        assert result["search_results"][0]["score"] == 0.92

    @pytest.mark.asyncio
    async def test_event_embedding_and_article_matching(self):
        """事件 embedding 写入 → 事件-文章语义关联"""
        # 1. 模拟事件创建和 embedding 写入
        mock_embedding_svc = MagicMock()
        mock_embedding_svc.is_ready.return_value = True
        mock_embedding_svc.embed = AsyncMock(return_value=[0.2] * 1024)

        mock_vector_repo = MagicMock()
        mock_vector_repo.add = AsyncMock()

        mock_event_repo = AsyncMock()
        created_event = MagicMock()
        created_event.event_id = "evt_001"
        created_event.title = "光伏行业政策扶持"
        created_event.summary = "国家出台光伏补贴政策"
        created_event.sentiment = "positive"
        created_event.affected_stocks = [{"code": "300750"}]
        created_event.affected_industries = [{"code": "new_energy"}]
        mock_event_repo.create = AsyncMock(return_value=created_event)

        mock_impact_article_repo = AsyncMock()
        mock_user_impact_repo = MagicMock()
        mock_user_impact_repo.session = AsyncMock()

        from app.application.use_cases.event_radar import EventRadarUseCase
        uc = EventRadarUseCase(
            event_repo=mock_event_repo,
            article_repo=mock_impact_article_repo,
            impact_repo=mock_user_impact_repo,
            vector_search_repo=mock_vector_repo,
            embedding_service=mock_embedding_svc,
        )

        # 2. 语义匹配
        mock_vector_repo.search = AsyncMock(return_value=[
            VectorSearchResult(
                doc_id="article_art_123",
                score=0.88,
                metadata={"title": "光伏政策扶持分析"},
                document="关于光伏政策的深度分析",
            ),
        ])

        from app.domain.entities.impact_event import ImpactEvent
        event = ImpactEvent(
            event_id="evt_001",
            title="光伏行业政策扶持",
            summary="国家出台光伏补贴政策",
            sentiment="positive",
            importance="high",
            affected_stocks=[{"code": "300750", "name": "宁德时代"}],
            affected_industries=[{"code": "new_energy", "name": "新能源"}],
            source_count=1,
        )

        results = await uc._find_related_analyses(event)

        assert len(results) == 1
        assert results[0]["similarity_score"] == 88.0  # 0.88 * 100

    @pytest.mark.asyncio
    async def test_rag_disabled_falls_back_to_fulltext(self):
        """关闭 RAG 后降级到 FULLTEXT"""
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

            from app.infrastructure.workflow.nodes.retrieve import create_retrieve_node
            node = create_retrieve_node(
                session_factory=mock_session_factory,
                vector_search_repo=MagicMock(),
                embedding_service=mock_embedding_svc,
            )

            result = await node({"raw_text": "测试降级检索", "user_id": "default"})

            # FULLTEXT 被调用
            MockSearchRepo.assert_called_once()
            assert result["search_results"] == []
