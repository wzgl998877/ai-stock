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

```
文章保存 (manage_article.py)
  → MySQL INSERT (现有逻辑)
  → EmbeddingService.embed(title + summary)
  → VectorSearchRepo.add(article_id, embedding, metadata)
  → [异步] EmbeddingService.embed(content)
  → VectorSearchRepo.update(article_id, content_embedding)

事件入库 (event_radar.py)
  → MySQL INSERT (现有逻辑)
  → EmbeddingService.embed(title + summary)
  → VectorSearchRepo.add(event_id, embedding, metadata)

检索 (retrieve.py)
  → EmbeddingService.embed(query)
  → VectorSearchRepo.search(query_embedding, top_k=3)
  → if empty → MySQLSearchRepository.search() (FULLTEXT 兜底)
  → return formatted results
```

## Relationships

```
ChromaDB knowledge_articles ←→ MySQL t_analysis_article (1:1, article_id)
ChromaDB impact_events      ←→ MySQL t_impact_event (1:1, event_id)
```

向量数据是 MySQL 数据的**派生索引**，不存储独立业务数据。任何 ChromaDB 数据丢失都可通过 MySQL 全量重建。
