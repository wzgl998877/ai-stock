"""存档相关单元测试 — 验证分析记录创建、增量更新、状态转换"""

import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock

from app.domain.entities.article import Article, StockRef
from app.infrastructure.repositories.mysql_article_repo import MySQLArticleRepository


def _make_article(**overrides) -> Article:
    defaults = dict(
        article_id=uuid.uuid4().hex,
        title="测试分析",
        summary="测试摘要",
        content="",
        event_type="other",
        raw_input="000001 平安银行",
        user_id="default_user",
        article_type="stock_analysis",
        analysis_data={"mode": "full", "agents": {}, "debates": [], "decision": {}},
        status="in_progress",
        stocks=[StockRef(stock_code="000001", stock_name="平安银行")],
    )
    defaults.update(overrides)
    return Article(**defaults)


class TestArticleEntity:
    """测试 Article Entity 新增字段"""

    def test_default_values(self):
        article = _make_article()
        assert article.article_type == "stock_analysis"
        assert article.status == "in_progress"
        assert article.analysis_data is not None
        assert article.analysis_data["mode"] == "full"

    def test_status_transitions(self):
        article = _make_article(status="in_progress")
        assert article.status == "in_progress"

        # 模拟完成
        article.status = "completed"
        assert article.status == "completed"

    def test_analysis_data_structure(self):
        data = {
            "mode": "quick",
            "agents": {
                "market": {"status": "done", "summary": "..."},
                "fundamentals": {"status": "done", "summary": "..."},
            },
            "debates": [],
            "decision": {"action": "买入", "confidence": 0.8},
        }
        article = _make_article(analysis_data=data)
        assert article.analysis_data["mode"] == "quick"
        assert len(article.analysis_data["agents"]) == 2


class TestAnalysisDataUpdate:
    """测试 update_analysis_data 逻辑"""

    @pytest.mark.anyio
    async def test_update_analysis_data_sets_fields(self):
        mock_session = AsyncMock()
        # scalar_one_or_none 是同步方法，用 MagicMock
        mock_result = MagicMock()

        mock_model = MagicMock()
        mock_model.article_id = "test123"
        mock_model.analysis_data = None
        mock_model.status = "in_progress"

        mock_result.scalar_one_or_none.return_value = mock_model
        mock_session.execute.return_value = mock_result

        repo = MySQLArticleRepository(mock_session)
        new_data = {"mode": "full", "agents": {"market": {"status": "done"}}}

        await repo.update_analysis_data("test123", new_data, "completed")

        assert mock_model.analysis_data == new_data
        assert mock_model.status == "completed"
        mock_session.flush.assert_called_once()

    @pytest.mark.anyio
    async def test_update_analysis_data_no_record(self):
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = MySQLArticleRepository(mock_session)
        # 不应抛异常
        await repo.update_analysis_data("nonexistent", {}, "stopped")
        mock_session.flush.assert_not_called()


class TestStatusStateMachine:
    """测试状态机转换：in_progress → completed / stopped"""

    def test_in_progress_to_completed(self):
        article = _make_article(status="in_progress")
        article.status = "completed"
        assert article.status == "completed"

    def test_in_progress_to_stopped(self):
        article = _make_article(status="in_progress")
        article.status = "stopped"
        assert article.status == "stopped"

    def test_default_status_is_completed(self):
        """已有记录默认 status 应为 completed"""
        article = Article(
            article_id="test",
            title="test",
            summary="test",
            content="test",
            event_type="other",
            raw_input="test",
            user_id="test",
        )
        assert article.status == "completed"
