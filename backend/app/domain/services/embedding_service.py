"""Embedding 服务抽象接口"""

from abc import ABC, abstractmethod


class EmbeddingService(ABC):
    """Embedding 服务 — Domain 层抽象，Infrastructure 层实现"""

    @abstractmethod
    def is_ready(self) -> bool:
        """模型是否已加载就绪。"""
        ...

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        """生成单条文本的 embedding 向量。"""
        ...

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """批量生成 embedding 向量。"""
        ...
