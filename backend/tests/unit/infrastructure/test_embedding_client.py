"""Embedding 客户端单元测试"""

import pytest
from unittest.mock import MagicMock, patch


class TestLocalEmbeddingService:
    """LocalEmbeddingService 单元测试"""

    def test_is_ready_when_model_loaded(self):
        """模型加载成功时 is_ready 返回 True"""
        with patch("app.infrastructure.vector.embedding_client.SentenceTransformer") as MockST:
            mock_model = MagicMock()
            mock_model.get_sentence_embedding_dimension.return_value = 1024
            MockST.return_value = mock_model

            from app.infrastructure.vector.embedding_client import LocalEmbeddingService
            svc = LocalEmbeddingService("test-model")

            assert svc.is_ready() is True

    def test_is_ready_when_model_load_fails(self):
        """模型加载失败时 is_ready 返回 False，不抛异常"""
        with patch("app.infrastructure.vector.embedding_client.SentenceTransformer") as MockST:
            MockST.side_effect = ImportError("No module")

            from app.infrastructure.vector.embedding_client import LocalEmbeddingService
            svc = LocalEmbeddingService("bad-model")

            assert svc.is_ready() is False

    @pytest.mark.asyncio
    async def test_embed_returns_vector(self):
        """embed 返回正确维度的向量"""
        with patch("app.infrastructure.vector.embedding_client.SentenceTransformer") as MockST:
            mock_model = MagicMock()
            mock_model.get_sentence_embedding_dimension.return_value = 1024
            import numpy as np
            mock_model.encode.return_value = np.random.rand(1024).astype(np.float32)
            MockST.return_value = mock_model

            from app.infrastructure.vector.embedding_client import LocalEmbeddingService
            svc = LocalEmbeddingService("test-model")

            result = await svc.embed("测试文本")
            assert isinstance(result, list)
            assert len(result) == 1024

    @pytest.mark.asyncio
    async def test_embed_empty_text_returns_zeros(self):
        """空文本返回零向量"""
        with patch("app.infrastructure.vector.embedding_client.SentenceTransformer") as MockST:
            mock_model = MagicMock()
            mock_model.get_sentence_embedding_dimension.return_value = 1024
            MockST.return_value = mock_model

            from app.infrastructure.vector.embedding_client import LocalEmbeddingService
            svc = LocalEmbeddingService("test-model")

            result = await svc.embed("")
            assert isinstance(result, list)
            assert len(result) == 1024
            assert all(v == 0.0 for v in result)

    @pytest.mark.asyncio
    async def test_embed_batch_returns_multiple_vectors(self):
        """embed_batch 批量返回向量"""
        with patch("app.infrastructure.vector.embedding_client.SentenceTransformer") as MockST:
            mock_model = MagicMock()
            mock_model.get_sentence_embedding_dimension.return_value = 1024
            import numpy as np
            mock_model.encode.return_value = np.random.rand(3, 1024).astype(np.float32)
            MockST.return_value = mock_model

            from app.infrastructure.vector.embedding_client import LocalEmbeddingService
            svc = LocalEmbeddingService("test-model")

            result = await svc.embed_batch(["文本1", "文本2", "文本3"])
            assert len(result) == 3
            assert all(len(v) == 1024 for v in result)

    @pytest.mark.asyncio
    async def test_embed_when_not_ready_raises(self):
        """模型未就绪时 embed 抛出 RuntimeError"""
        with patch("app.infrastructure.vector.embedding_client.SentenceTransformer") as MockST:
            MockST.side_effect = ImportError("No module")

            from app.infrastructure.vector.embedding_client import LocalEmbeddingService
            svc = LocalEmbeddingService("bad-model")

            with pytest.raises(RuntimeError, match="未就绪"):
                await svc.embed("测试")
