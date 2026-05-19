"""ChromaDB 存储单元测试"""

import pytest
from unittest.mock import MagicMock, patch
import numpy as np


class TestChromaVectorStore:
    """ChromaVectorStore 单元测试"""

    @pytest.fixture
    def mock_chroma(self):
        """创建 mock ChromaDB 客户端和集合"""
        with patch("app.infrastructure.vector.chroma_store.chromadb") as mock_chromadb:
            mock_client = MagicMock()
            mock_collection = MagicMock()
            mock_client.get_or_create_collection.return_value = mock_collection
            mock_chromadb.PersistentClient.return_value = mock_client
            yield mock_client, mock_collection

    def test_get_or_create_collection(self, mock_chroma):
        mock_client, mock_collection = mock_chroma
        from app.infrastructure.vector.chroma_store import ChromaVectorStore

        store = ChromaVectorStore("./test_db")
        result = store.get_or_create_collection("test_col")

        mock_client.get_or_create_collection.assert_called_once_with(
            name="test_col",
            metadata={"hnsw:space": "cosine"},
        )
        assert result == mock_collection

    def test_add_documents(self, mock_chroma):
        mock_client, mock_collection = mock_chroma
        from app.infrastructure.vector.chroma_store import ChromaVectorStore

        store = ChromaVectorStore("./test_db")
        store.add_documents(
            collection_name="test_col",
            ids=["doc1"],
            embeddings=[[0.1] * 1024],
            metadatas=[{"title": "test"}],
            documents=["test doc"],
        )

        mock_collection.add.assert_called_once_with(
            ids=["doc1"],
            embeddings=[[0.1] * 1024],
            metadatas=[{"title": "test"}],
            documents=["test doc"],
        )

    def test_query_returns_formatted_results(self, mock_chroma):
        mock_client, mock_collection = mock_chroma
        from app.infrastructure.vector.chroma_store import ChromaVectorStore

        # 模拟 ChromaDB query 返回结构
        mock_collection.query.return_value = {
            "ids": [["doc1", "doc2"]],
            "distances": [[0.1, 0.5]],
            "metadatas": [[{"title": "a"}, {"title": "b"}]],
            "documents": [["text1", "text2"]],
        }

        store = ChromaVectorStore("./test_db")
        results = store.query("test_col", [0.1] * 1024, top_k=2)

        assert len(results) == 2
        assert results[0]["id"] == "doc1"
        assert results[0]["distance"] == 0.1
        assert results[0]["metadata"]["title"] == "a"
        assert results[1]["id"] == "doc2"

    def test_delete(self, mock_chroma):
        mock_client, mock_collection = mock_chroma
        from app.infrastructure.vector.chroma_store import ChromaVectorStore

        store = ChromaVectorStore("./test_db")
        store.delete("test_col", ["doc1"])

        mock_collection.delete.assert_called_once_with(ids=["doc1"])

    def test_update_with_embedding(self, mock_chroma):
        mock_client, mock_collection = mock_chroma
        from app.infrastructure.vector.chroma_store import ChromaVectorStore

        store = ChromaVectorStore("./test_db")
        store.update("test_col", "doc1", embedding=[0.2] * 1024, metadata={"title": "updated"})

        mock_collection.update.assert_called_once_with(
            ids=["doc1"],
            embeddings=[[0.2] * 1024],
            metadatas=[{"title": "updated"}],
        )
