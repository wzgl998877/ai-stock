"""本地 Embedding 客户端 — 基于 sentence-transformers 加载 bge-large-zh-v1.5"""

import logging
from typing import Optional

from app.domain.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


class LocalEmbeddingService(EmbeddingService):
    """本地 sentence-transformers Embedding 服务"""

    def __init__(self, model_name: str = "BAAI/bge-large-zh-v1.5"):
        self._model_name = model_name
        self._model: Optional[object] = None
        self._ready = False
        self._load_model()

    def _load_model(self) -> None:
        """加载 sentence-transformers 模型"""
        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self._model_name)
            self._ready = True
            dim = self._model.get_sentence_embedding_dimension()
            logger.info(
                "Embedding 模型加载成功: %s (dim=%d)", self._model_name, dim
            )
        except Exception as e:
            logger.warning(
                "Embedding 模型加载失败: %s, RAG 将降级到 FULLTEXT 模式: %s",
                self._model_name,
                e,
            )
            self._ready = False

    def is_ready(self) -> bool:
        return self._ready

    async def embed(self, text: str) -> list[float]:
        """生成单条文本的 embedding 向量"""
        if not self._ready or self._model is None:
            raise RuntimeError("Embedding 模型未就绪")
        if not text or not text.strip():
            # 空文本返回零向量（避免报错）
            dim = self._model.get_sentence_embedding_dimension()
            return [0.0] * dim
        embedding = self._model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """批量生成 embedding 向量"""
        if not self._ready or self._model is None:
            raise RuntimeError("Embedding 模型未就绪")
        dim = self._model.get_sentence_embedding_dimension()
        # 处理空文本
        processed = [t if t and t.strip() else "" for t in texts]
        embeddings = self._model.encode(processed, normalize_embeddings=True)
        result = []
        for i, emb in enumerate(embeddings):
            if processed[i] == "":
                result.append([0.0] * dim)
            else:
                result.append(emb.tolist())
        return result
