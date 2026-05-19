"""向量检索仓储抽象接口"""

from abc import ABC, abstractmethod

from app.domain.entities.vector_search import VectorSearchResult


class VectorSearchRepository(ABC):
    """向量检索仓储 — Domain 层抽象，Infrastructure 层实现"""

    @abstractmethod
    async def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        filters: dict | None = None,
        threshold: float = 0.7,
        collection: str = "knowledge_articles",
    ) -> list[VectorSearchResult]:
        """语义向量检索。

        Args:
            query_embedding: query 文本的 embedding 向量
            top_k: 返回最多 top_k 个结果
            filters: metadata 过滤条件，如 {"user_id": "default"}
            threshold: 最低相似度阈值，低于此值的结果被过滤
            collection: 目标集合名称
        Returns:
            按相似度降序排列的检索结果列表
        """
        ...

    @abstractmethod
    async def add(
        self,
        collection: str,
        doc_id: str,
        embedding: list[float],
        metadata: dict,
        document: str,
    ) -> None:
        """新增文档向量。"""
        ...

    @abstractmethod
    async def delete(
        self,
        collection: str,
        doc_id: str,
    ) -> None:
        """删除文档向量。"""
        ...

    @abstractmethod
    async def update(
        self,
        collection: str,
        doc_id: str,
        embedding: list[float] | None = None,
        metadata: dict | None = None,
    ) -> None:
        """更新文档向量或元数据。"""
        ...
