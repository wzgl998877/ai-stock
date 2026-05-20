"""向量检索仓储实现 — 基于 ChromaDB"""

import logging

from app.domain.entities.vector_search import VectorSearchResult
from app.domain.repositories.vector_search_repo import VectorSearchRepository
from app.infrastructure.vector.chroma_store import ChromaVectorStore

logger = logging.getLogger(__name__)


class ChromaVectorSearchRepo(VectorSearchRepository):
    """ChromaDB 向量检索仓储实现"""

    def __init__(self, store: ChromaVectorStore):
        self._store = store

    async def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        filters: dict | None = None,
        threshold: float = 0.7,
        collection: str = "knowledge_articles",
    ) -> list[VectorSearchResult]:
        """语义向量检索，返回相似度 >= threshold 的结果"""
        raw_results = self._store.query(
            collection_name=collection,
            query_embedding=query_embedding,
            top_k=top_k,
            where=filters,
        )

        # 过滤低于阈值的结果并转换为领域实体
        results = []
        for item in raw_results:
            # ChromaDB cosine space: distance = 1 - similarity
            similarity = 1.0 - item["distance"]
            if similarity >= threshold:
                results.append(
                    VectorSearchResult(
                        doc_id=item["id"],
                        score=similarity,
                        metadata=item.get("metadata", {}),
                        document=item.get("document", ""),
                    )
                )

        logger.debug(
            "向量检索 %s: 返回 %d/%d 条 (threshold=%.2f)",
            collection,
            len(results),
            len(raw_results),
            threshold,
        )
        return results

    async def add(
        self,
        collection: str,
        doc_id: str,
        embedding: list[float],
        metadata: dict,
        document: str,
    ) -> None:
        """新增文档向量"""
        self._store.add_documents(
            collection_name=collection,
            ids=[doc_id],
            embeddings=[embedding],
            metadatas=[metadata],
            documents=[document],
        )

    async def delete(
        self,
        collection: str,
        doc_id: str,
    ) -> None:
        """删除文档向量"""
        self._store.delete(collection_name=collection, ids=[doc_id])

    async def update(
        self,
        collection: str,
        doc_id: str,
        embedding: list[float] | None = None,
        metadata: dict | None = None,
    ) -> None:
        """更新文档向量或元数据"""
        self._store.update(
            collection_name=collection,
            doc_id=doc_id,
            embedding=embedding,
            metadata=metadata,
        )

    async def delete_by_filter(
        self,
        collection: str,
        filters: dict,
    ) -> int:
        """按 metadata 条件批量删除文档，返回删除数量"""
        return self._store.delete_by_filter(collection_name=collection, where=filters)
