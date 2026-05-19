# Data Model: RAG 语义检索增强

**Feature**: 008-rag-semantic-retrieval
**Date**: 2026-05-19

## Overview

RAG 功能不新增 MySQL 表，而是在 ChromaDB 中维护两套向量集合。向量数据是 MySQL 主数据的派生索引，可从 MySQL 全量重建。

## ChromaDB Collections

### Collection: `knowledge_articles`

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | `article_{article_id}`（MySQL t_analysis_article.article_id） |
| embedding | float[1024] | 标题+摘要拼接文本的 bge-large-zh-v1.5 向量 |
| document | string | 标题+摘要拼接文本（用于 ChromaDB 内部检索展示） |
| metadata.user_id | int | 用户 ID（数据隔离） |
| metadata.title | string | 文章标题 |
| metadata.stock_codes | string | 关联股票代码，逗号分隔（如 "300750,601857"） |
| metadata.industries | string | 关联行业名称，逗号分隔 |
| metadata.event_type | string | 事件类型（geopolitical/policy/earnings/industry/macro/other） |

### Collection: `impact_events`

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | `event_{event_id}`（MySQL t_impact_event.event_id） |
| embedding | float[1024] | 标题+摘要拼接文本的 bge-large-zh-v1.5 向量 |
| document | string | 标题+摘要拼接文本 |
| metadata.title | string | 事件标题 |
| metadata.affected_stocks | string | 受影响股票代码，逗号分隔 |
| metadata.affected_industries | string | 受影响行业名称，逗号分隔 |
| metadata.sentiment | string | 情感倾向（positive/negative/neutral） |

## Domain Entities

### VectorSearchResult

```python
@dataclass
class VectorSearchResult:
    doc_id: str               # 文档 ID（article_xxx 或 event_xxx）
    score: float              # cosine similarity 分数 [0, 1]
    metadata: dict            # ChromaDB metadata
    document: str             # 原始文档文本
```

### EmbeddingData

```python
@dataclass
class EmbeddingData:
    doc_id: str               # 文档 ID
    embedding: list[float]    # 1024 维向量
    metadata: dict            # 元数据
    document: str             # 原始文本
```

## Data Flow

### 1. 文章保存 → 向量写入（SaveArticleUseCase）

```
analysis.py Router
  │ 从 request.app.state 获取 embedding_service / vector_search_repo
  ▼
SaveArticleUseCase.execute(...)
  ├─ article_repo.save(article)           → MySQL INSERT → 获得 article_id
  ├─ embed_text = f"{title}\n{summary}"
  ├─ embedding = embedding_service.embed(embed_text)    → 1024 维向量
  ├─ metadata = {user_id, title, stock_codes, industries, event_type}
  ├─ vector_search_repo.add("knowledge_articles", f"article_{id}", embedding, metadata, document)
  └─ try-except: 失败不阻塞，日志告警

删除文章 → vector_search_repo.delete("knowledge_articles", f"article_{id}")
更新文章 → vector_search_repo.update("knowledge_articles", f"article_{id}", new_embedding, new_metadata)
```

### 2. 事件入库 → 向量写入（EventRadarUseCase.crawl_and_process）

```
EventRadarUseCase.crawl_and_process()
  ├─ ClsProvider().fetch_latest(50)       → 采集财经新闻
  ├─ assess_event()                       → 去重 + 影响判断
  ├─ event_repo.create(event)             → MySQL INSERT → 获得 event_id
  ├─ embed_text = f"{event.title}\n{event.summary}"
  ├─ embedding = embedding_service.embed(embed_text)
  ├─ metadata = {title, affected_stocks, affected_industries, sentiment}
  ├─ vector_search_repo.add("impact_events", f"event_{id}", embedding, metadata, document)
  ├─ article_repo.create(impact_article)  → 来源文章入库
  └─ _match_users_for_events()            → 用户匹配 + 预警

每条事件 embedding 生成约 50-100ms，50 条增量约 2.5-5s
```

### 3. 语义检索（retrieve node）

```
retrieve_node(state)
  ├─ embed_text = state["raw_text"][:80]
  ├─ embedding = embedding_service.embed(embed_text)
  ├─ results = vector_search_repo.search(embedding, top_k=3, filters={user_id}, threshold=0.7)
  ├─ if not results:
  │    └─ MySQLSearchRepository.search(query, user_id, page=1, page_size=3)  → FULLTEXT 兜底
  └─ return {"search_results": formatted_results}    → 格式与现有一致
```

### 4. 事件-文章语义关联（event_radar._find_related_analyses）

```
_find_related_analyses(event) [改造]
  ├─ embed_text = f"{event.title}\n{event.summary}"
  ├─ embedding = embedding_service.embed(embed_text)
  ├─ results = vector_search_repo.search(embedding, top_k=3, collection="knowledge_articles", threshold=0.7)
  ├─ if not results:
  │    └─ 回退到现有行业+股票交集匹配（_find_related_analyses 原有逻辑）
  └─ return [{article_id, title, summary, similarity_score}, ...]
```

### 5. 事件去重增强（event_dedup.py）

```
is_duplicate_event(new_title, new_url, existing_hashes, existing_titles, embedding_service, vector_repo)
  ├─ URL hash 精确匹配（最快，现有逻辑）
  ├─ Jaccard 字符相似度 ≥ 0.6（现有逻辑）
  ├─ [新增] 语义 embedding 相似度 ≥ 0.85
  │    ├─ new_embedding = embedding_service.embed(new_title)
  │    ├─ 在 impact_events 集合中搜索相似向量
  │    └─ top-1 result.score >= 0.85 → 判定重复
  └─ 三层任一命中即判定重复
```

### 6. 服务初始化（main.py lifespan）

```
lifespan(app)
  ├─ embedding_service = LocalEmbeddingService(model="BAAI/bge-large-zh-v1.5")
  ├─ chroma_store = ChromaVectorStore(persist_dir="./data/vector_db")
  ├─ vector_search_repo = ChromaVectorSearchRepo(chroma_store)
  ├─ app.state.embedding_service = embedding_service
  ├─ app.state.vector_search_repo = vector_search_repo
  ├─ build_analysis_graph(..., vector_search_repo, embedding_service)
  └─ setup_scheduler(..., vector_search_repo, embedding_service)
```

### 7. 向量重建（运维脚本）

```
scripts/rebuild_vector_index.py
  ├─ SELECT * FROM t_analysis_article WHERE status='completed' AND deleted='0'
  ├─ embed_batch([title+summary, ...]) → 每批 32 条
  ├─ 写入 knowledge_articles 集合
  ├─ SELECT * FROM t_impact_event
  ├─ embed_batch([title+summary, ...]) → 每批 32 条
  └─ 写入 impact_events 集合
```

## Relationships

```
ChromaDB knowledge_articles ←→ MySQL t_analysis_article (1:1, article_id)
ChromaDB impact_events      ←→ MySQL t_impact_event (1:1, event_id)
```

向量数据是 MySQL 数据的**派生索引**，不存储独立业务数据。任何 ChromaDB 数据丢失都可通过 MySQL 全量重建。
