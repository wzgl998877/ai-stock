# Contract: Vector Search Interface (Domain Layer)

**Feature**: 008-rag-semantic-retrieval
**Date**: 2026-05-19

## Overview

RAG 改造不引入新的 REST API 端点（前端零改动），契约变更仅限于后端内部 Domain 层接口。

## New Abstract Interfaces

### VectorSearchRepository (domain/repositories/vector_search_repo.py)

```python
from abc import ABC, abstractmethod

class VectorSearchRepository(ABC):
    @abstractmethod
    async def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        filters: dict | None = None,
        threshold: float = 0.7,
    ) -> list[VectorSearchResult]:
        """语义向量检索。
        Args:
            query_embedding: query 文本的 embedding 向量
            top_k: 返回最多 top_k 个结果
            filters: metadata 过滤条件，如 {"user_id": 1}
            threshold: 最低相似度阈值，低于此值的结果被过滤
        Returns:
            按相似度降序排列的检索结果列表
        """
        ...

    @abstractmethod
    async def add(
        self,
        collection: str,      # "knowledge_articles" | "impact_events"
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
```

### EmbeddingService (domain/services/embedding_service.py)

```python
from abc import ABC, abstractmethod

class EmbeddingService(ABC):
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
```

## Modified Internal Interfaces

### retrieve node (infrastructure/workflow/nodes/retrieve.py)

**Before**: `create_retrieve_node(session_factory)`
**After**: `create_retrieve_node(session_factory, vector_search_repo=None, embedding_service=None)`

- 新增可选参数 `vector_search_repo` 和 `embedding_service`
- 当两者都可用时，优先向量检索，无结果回退 FULLTEXT
- 当任一不可用时，直接走 FULLTEXT（与现有行为一致）

### SaveArticleUseCase (application/use_cases/manage_article.py)

**Before**: `__init__(article_repo, industry_repo)`
**After**: `__init__(article_repo, industry_repo, vector_search_repo=None, embedding_service=None)`

- 新增可选参数
- 保存文章后，如果向量服务可用，生成 embedding 并写入 ChromaDB
- 向量写入失败不阻塞文章保存

**详细调用链**：
```python
async def execute(self, ...) -> Article:
    # ... 现有验证、构建实体逻辑不变 ...
    saved = await self.article_repo.save(article)
    # 新增：向量写入
    if self.vector_search_repo and self.embedding_service and self.embedding_service.is_ready():
        try:
            embed_text = f"{saved.title}\n{saved.summary}"
            embedding = await self.embedding_service.embed(embed_text)
            metadata = {
                "user_id": saved.user_id,
                "title": saved.title,
                "stock_codes": ",".join(s.stock_code for s in saved.stocks),
                "industries": ",".join(i.industry_code for i in saved.industries),
                "event_type": saved.event_type,
            }
            await self.vector_search_repo.add(
                collection="knowledge_articles",
                doc_id=f"article_{saved.article_id}",
                embedding=embedding,
                metadata=metadata,
                document=embed_text,
            )
        except Exception as e:
            logger.warning("文章 embedding 写入失败(article_id=%s): %s", saved.article_id, e)
    return saved
```

### DeleteArticleUseCase (application/use_cases/manage_article.py)

**Before**: `__init__(article_repo)`
**After**: `__init__(article_repo, vector_search_repo=None)`

- 软删除文章后，同步删除 ChromaDB 中对应向量
- 向量删除失败不阻塞删除操作

### EventRadarUseCase (application/use_cases/event_radar.py)

**Before**: `__init__(event_repo, article_repo, impact_repo, ai_service=None)`
**After**: `__init__(event_repo, article_repo, impact_repo, ai_service=None, vector_search_repo=None, embedding_service=None)`

- `crawl_and_process()`: 事件入库后生成 embedding 写入 ChromaDB（详见 research.md R9.2）
- `_find_related_analyses()`: 从行业+股票交集匹配升级为语义检索 + 交集兜底

### analysis.py Router (routers/analysis.py)

**改造**: 保存文章路由中注入向量服务
```python
# 从 app.state 获取全局向量服务
embedding_svc = request.app.state.embedding_service
vector_repo = request.app.state.vector_search_repo
use_case = SaveArticleUseCase(article_repo, industry_repo, vector_repo, embedding_svc)
```

### main.py lifespan

**改造**: 初始化并注入向量服务
```python
# 初始化 Embedding + ChromaDB
if settings.RAG_ENABLED:
    embedding_service = LocalEmbeddingService(model_name=settings.RAG_EMBEDDING_MODEL)
    chroma_store = ChromaVectorStore(persist_dir=settings.RAG_VECTOR_DB_PATH)
    vector_search_repo = ChromaVectorSearchRepo(chroma_store)
else:
    embedding_service = None
    vector_search_repo = None
app.state.embedding_service = embedding_service
app.state.vector_search_repo = vector_search_repo
# 注入到 LangGraph 和调度器
build_analysis_graph(..., vector_search_repo=vector_search_repo, embedding_service=embedding_service)
setup_scheduler(..., vector_search_repo=vector_search_repo, embedding_service=embedding_service)
```

## No API Changes

所有外部 API 端点（Router 层）契约不变：

| Endpoint | 变更 |
|----------|------|
| `GET /api/knowledge/search` | 无变更（Phase 3 再改） |
| `POST (SSE) /api/chat/sessions/{id}/stream` | 无变更（内部 retrieve 节点改造） |
| `GET /api/v1/event-radar/impacts` | 无变更（内部关联逻辑改造） |
| `POST /api/analysis/articles` | 无变更（内部 embedding 生成） |
