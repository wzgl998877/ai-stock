"""向量检索仓储单元测试"""

import pytest
from unittest.mock import MagicMock, patch


class TestChromaVectorSearchRepo:
    """ChromaVectorSearchRepo 单元测试"""

    @pytest.fixture
    def repo(self):
        """创建测试用仓储实例"""
        mock_store = MagicMock()
        from app.infrastructure.repositories.chroma_vector_search_repo import ChromaVectorSearchRepo
        return ChromaVectorSearchRepo(mock_store), mock_store

    @pytest.mark.asyncio
    async def test_search_filters_by_threshold(self, repo):
        search_repo, mock_store = repo

        # 模拟 ChromaDB 返回：distance 0.2 (similarity=0.8) 和 0.6 (similarity=0.4)
        mock_store.query.return_value = [
            {"id": "doc1", "distance": 0.2, "metadata": {"title": "a"}, "document": "text1"},
            {"id": "doc2", "distance": 0.6, "metadata": {"title": "b"}, "document": "text2"},
        ]

        results = await search_repo.search(
            query_embedding=[0.1] * 1024,
            top_k=5,
            threshold=0.7,
            collection="knowledge_articles",
        )

        # 只有 doc1 (similarity=0.8) 通过 threshold 0.7
        assert len(results) == 1
        assert results[0].doc_id == "doc1"
        assert results[0].score == pytest.approx(0.8, abs=0.01)

    @pytest.mark.asyncio
    async def test_search_returns_empty_when_all_below_threshold(self, repo):
        search_repo, mock_store = repo

        mock_store.query.return_value = [
            {"id": "doc1", "distance": 0.9, "metadata": {}, "document": ""},
        ]

        results = await search_repo.search(
            query_embedding=[0.1] * 1024,
            threshold=0.7,
        )

        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_add_delegates_to_store(self, repo):
        search_repo, mock_store = repo

        await search_repo.add(
            collection="knowledge_articles",
            doc_id="article_1",
            embedding=[0.1] * 1024,
            metadata={"title": "test"},
            document="test doc",
        )

        mock_store.add_documents.assert_called_once_with(
            collection_name="knowledge_articles",
            ids=["article_1"],
            embeddings=[[0.1] * 1024],
            metadatas=[{"title": "test"}],
            documents=["test doc"],
        )

    @pytest.mark.asyncio
    async def test_delete_delegates_to_store(self, repo):
        search_repo, mock_store = repo

        await search_repo.delete("knowledge_articles", "article_1")

        mock_store.delete.assert_called_once_with(
            collection_name="knowledge_articles",
            ids=["article_1"],
        )

    @pytest.mark.asyncio
    async def test_update_delegates_to_store(self, repo):
        search_repo, mock_store = repo

        await search_repo.update(
            collection="knowledge_articles",
            doc_id="article_1",
            embedding=[0.2] * 1024,
            metadata={"title": "updated"},
        )

        mock_store.update.assert_called_once_with(
            collection_name="knowledge_articles",
            doc_id="article_1",
            embedding=[0.2] * 1024,
            metadata={"title": "updated"},
        )

    @pytest.mark.asyncio
    async def test_search_with_metadata_filter(self, repo):
        search_repo, mock_store = repo

        mock_store.query.return_value = [
            {"id": "doc1", "distance": 0.1, "metadata": {"user_id": "u1"}, "document": "text"},
        ]

        await search_repo.search(
            query_embedding=[0.1] * 1024,
            filters={"user_id": "u1"},
            threshold=0.7,
        )

        mock_store.query.assert_called_once_with(
            collection_name="knowledge_articles",
            query_embedding=[0.1] * 1024,
            top_k=5,
            where={"user_id": "u1"},
        )
