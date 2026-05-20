"""向量检索领域实体"""

from dataclasses import dataclass, field


@dataclass
class VectorSearchResult:
    """向量检索结果"""

    doc_id: str  # 文档 ID（article_xxx 或 event_xxx）
    score: float  # cosine similarity 分数 [0, 1]
    metadata: dict  # ChromaDB metadata
    document: str  # 原始文档文本


@dataclass
class Chunk:
    """文章切分块"""

    index: int       # 块序号，0 = 标题摘要块
    content: str     # 块文本
    chunk_type: str  # "summary" | "content"


@dataclass
class EmbeddingData:
    """待写入的 embedding 数据"""

    doc_id: str  # 文档 ID
    embedding: list[float]  # 1024 维向量
    metadata: dict  # 元数据
    document: str  # 原始文本
