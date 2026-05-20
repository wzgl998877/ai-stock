"""ChromaDB 存储封装 — 管理向量集合的 CRUD 操作"""

import logging
from typing import Optional

import chromadb

logger = logging.getLogger(__name__)


class ChromaVectorStore:
    """ChromaDB 向量存储封装"""

    def __init__(self, persist_dir: str = "./data/vector_db"):
        self._client = chromadb.PersistentClient(path=persist_dir)
        logger.info("ChromaDB 初始化完成: %s", persist_dir)

    def get_or_create_collection(self, name: str):
        """获取或创建集合"""
        return self._client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"},
        )

    def add_documents(
        self,
        collection_name: str,
        ids: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict],
        documents: list[str],
    ) -> None:
        """批量添加文档到集合"""
        collection = self.get_or_create_collection(collection_name)
        collection.add(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=documents,
        )
        logger.debug("ChromaDB 写入 %d 条到 %s", len(ids), collection_name)

    def query(
        self,
        collection_name: str,
        query_embedding: list[float],
        top_k: int = 5,
        where: Optional[dict] = None,
    ) -> list[dict]:
        """在集合中检索最相似的文档

        Returns:
            [{"id": str, "distance": float, "metadata": dict, "document": str}, ...]
        """
        collection = self.get_or_create_collection(collection_name)
        kwargs = {
            "query_embeddings": [query_embedding],
            "n_results": top_k,
        }
        if where:
            kwargs["where"] = where

        results = collection.query(**kwargs)

        # 解析 ChromaDB 返回结构
        formatted = []
        if results and results["ids"] and results["ids"][0]:
            ids = results["ids"][0]
            distances = results["distances"][0] if results["distances"] else [0.0] * len(ids)
            metadatas = results["metadatas"][0] if results["metadatas"] else [{}] * len(ids)
            documents = results["documents"][0] if results["documents"] else [""] * len(ids)

            for i, doc_id in enumerate(ids):
                formatted.append({
                    "id": doc_id,
                    "distance": distances[i],
                    "metadata": metadatas[i] if metadatas else {},
                    "document": documents[i] if documents else "",
                })

        return formatted

    def delete(self, collection_name: str, ids: list[str]) -> None:
        """从集合中删除文档"""
        collection = self.get_or_create_collection(collection_name)
        collection.delete(ids=ids)
        logger.debug("ChromaDB 删除 %d 条 from %s", len(ids), collection_name)

    def update(
        self,
        collection_name: str,
        doc_id: str,
        embedding: Optional[list[float]] = None,
        metadata: Optional[dict] = None,
    ) -> None:
        """更新集合中的文档向量或元数据"""
        collection = self.get_or_create_collection(collection_name)
        kwargs = {"ids": [doc_id]}
        if embedding is not None:
            kwargs["embeddings"] = [embedding]
        if metadata is not None:
            kwargs["metadatas"] = [metadata]
        collection.update(**kwargs)
        logger.debug("ChromaDB 更新 %s in %s", doc_id, collection_name)

    def get_by_filter(
        self,
        collection_name: str,
        where: dict,
    ) -> list[dict]:
        """按 metadata 条件查询文档，返回 [{"id": ..., "metadata": ...}, ...]"""
        collection = self.get_or_create_collection(collection_name)
        results = collection.get(where=where)
        return [
            {"id": id_, "metadata": meta}
            for id_, meta in zip(results["ids"], results["metadatas"] or [])
        ]

    def delete_by_filter(
        self,
        collection_name: str,
        where: dict,
    ) -> int:
        """按 metadata 条件批量删除文档，返回删除数量"""
        records = self.get_by_filter(collection_name, where)
        if not records:
            return 0
        ids = [r["id"] for r in records]
        self.delete(collection_name, ids=ids)
        return len(ids)

    def delete_collection(self, collection_name: str) -> bool:
        """删除整个集合，返回是否成功"""
        try:
            self._client.delete_collection(collection_name)
            logger.info("ChromaDB 集合已删除: %s", collection_name)
            return True
        except Exception as e:
            logger.warning("ChromaDB 删除集合失败(%s): %s", collection_name, e)
            return False
