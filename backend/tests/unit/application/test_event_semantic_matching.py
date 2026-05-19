"""事件语义关联单元测试"""

import pytest
from unittest.mock import MagicMock, AsyncMock

from app.domain.entities.impact_event import ImpactEvent
from app.domain.entities.vector_search import VectorSearchResult


def _make_event(title="新能源政策调整", summary="国务院发布新能源补贴政策"):
    return ImpactEvent(
        event_id="evt_001",
        title=title,
        summary=summary,
        sentiment="positive",
        importance="high",
        affected_stocks=[{"code": "300750", "name": "宁德时代"}],
        affected_industries=[{"code": "new_energy", "name": "新能源"}],
        source_count=1,
    )


class TestEventSemanticMatching:
    """事件语义关联单元测试"""

    @pytest.mark.asyncio
    async def test_semantic_matching_returns_articles_with_percentage(self):
        """语义匹配返回相关文章含百分比"""
        mock_embedding_svc = MagicMock()
        mock_embedding_svc.is_ready.return_value = True
        mock_embedding_svc.embed = AsyncMock(return_value=[0.1] * 1024)

        mock_vector_repo = MagicMock()
        mock_vector_repo.search = AsyncMock(return_value=[
            VectorSearchResult(
                doc_id="article_art_123",
                score=0.85,
                metadata={"title": "光伏政策扶持分析", "event_type": "policy"},
                document="关于光伏政策的分析",
            ),
        ])

        from app.application.use_cases.event_radar import EventRadarUseCase
        uc = EventRadarUseCase(
            event_repo=MagicMock(),
            article_repo=MagicMock(),
            impact_repo=MagicMock(),
            vector_search_repo=mock_vector_repo,
            embedding_service=mock_embedding_svc,
        )

        results = await uc._find_related_analyses(_make_event())

        assert len(results) == 1
        assert results[0]["similarity_score"] == 85.0  # 0.85 * 100
        assert results[0]["title"] == "光伏政策扶持分析"

    @pytest.mark.asyncio
    async def test_semantic_empty_falls_back_to_intersection(self):
        """无语义结果时回退行业+股票交集"""
        mock_embedding_svc = MagicMock()
        mock_embedding_svc.is_ready.return_value = True
        mock_embedding_svc.embed = AsyncMock(return_value=[0.1] * 1024)

        mock_vector_repo = MagicMock()
        mock_vector_repo.search = AsyncMock(return_value=[])

        # Mock session for SQL fallback
        mock_session = AsyncMock()
        mock_impact_repo = MagicMock()
        mock_impact_repo.session = mock_session

        # Mock SQL query results - return empty
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        from app.application.use_cases.event_radar import EventRadarUseCase
        uc = EventRadarUseCase(
            event_repo=MagicMock(),
            article_repo=MagicMock(),
            impact_repo=mock_impact_repo,
            vector_search_repo=mock_vector_repo,
            embedding_service=mock_embedding_svc,
        )

        results = await uc._find_related_analyses(_make_event())
        # Fallback returns empty because SQL mock returns empty
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_embedding_not_available_uses_intersection(self):
        """embedding 不可用时走原有逻辑"""
        mock_embedding_svc = MagicMock()
        mock_embedding_svc.is_ready.return_value = False

        mock_session = AsyncMock()
        mock_impact_repo = MagicMock()
        mock_impact_repo.session = mock_session

        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        from app.application.use_cases.event_radar import EventRadarUseCase
        uc = EventRadarUseCase(
            event_repo=MagicMock(),
            article_repo=MagicMock(),
            impact_repo=mock_impact_repo,
            vector_search_repo=MagicMock(),
            embedding_service=mock_embedding_svc,
        )

        results = await uc._find_related_analyses(_make_event())
        assert isinstance(results, list)
