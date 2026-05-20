# 计划：文章内容切分（Chunking）增强 RAG 检索质量

**分支**: `008-rag-semantic-retrieval` | **日期**: 2026-05-20 | **关联 Spec**: `specs/008-rag-semantic-retrieval/`

---

## Context

当前 RAG 实现只将文章的 `title + summary`（几十到几百字）作为单条向量存入 ChromaDB，正文 `content` 完全未参与 embedding。导致检索只能匹配标题/摘要级别的相似度，无法命中正文中的具体分析内容。

**目标**：将文章正文切分为多个语义 chunk，每个 chunk 独立生成 embedding 存入向量库，检索时合并同一文章的多个命中 chunk，提升检索召回率和上下文质量。

**改动范围**：仅针对 `knowledge_articles` 集合，`impact_events` 不做分块（事件本身只有 title+summary，无长正文）。

---

## 改动文件总览

| 文件 | 操作 | 说明 |
|------|------|------|
| `app/domain/services/text_chunker.py` | **新增** | 文章切分纯函数 |
| `app/domain/services/search_result_merger.py` | **新增** | 检索结果合并去重函数 |
| `app/domain/repositories/vector_search_repo.py` | 修改 | 新增 `delete_by_filter` 抽象方法 |
| `app/infrastructure/vector/chroma_store.py` | 修改 | 新增 `get_by_filter` 方法 |
| `app/infrastructure/repositories/chroma_vector_search_repo.py` | 修改 | 实现 `delete_by_filter` |
| `app/application/use_cases/manage_article.py` | 修改 | SaveArticleUseCase chunk 化写入；DeleteArticleUseCase 按过滤删除 |
| `app/infrastructure/workflow/nodes/retrieve.py` | 修改 | 使用 merge + top_k 调大 |
| `app/infrastructure/workflow/nodes/stock_news_analyst.py` | 修改 | 使用 merge + top_k 调大 |
| `app/application/use_cases/event_radar.py` | 修改 | `_find_related_analyses` 合并去重 |
| `scripts/rebuild_vector_index.py` | 修改 | 查 content 字段 + chunk 级写入 |
| `tests/unit/domain/test_text_chunker.py` | **新增** | 切分函数单元测试 |
| `tests/unit/domain/test_search_result_merger.py` | **新增** | 合并去重函数单元测试 |

---

## Step 1: 新增切分服务 `text_chunker.py`

**文件**: `backend/app/domain/services/text_chunker.py`（新建）

### 切分策略——段落级递归切分

1. **chunk_0**：`title + summary`，始终作为第一个 chunk（保留标题级匹配能力）
2. 正文按 `\n\n` 分段
3. 短段落（< `min_size` 字）与下一段合并
4. 长段落（> `max_size` 字）按中文句号/问号/感叹号断开

### 数据结构

```python
from dataclasses import dataclass

@dataclass
class Chunk:
    index: int       # 块序号，0 = 标题摘要块
    content: str     # 块文本
    chunk_type: str  # "summary" | "content"
```

### 函数签名

```python
def chunk_article(
    title: str,
    summary: str,
    content: str,
    min_size: int = 200,
    max_size: int = 800,
) -> list[Chunk]:
    """将文章切分为语义 chunk 列表。

    Returns:
        始终返回至少一个 Chunk（chunk_0 = title + summary）。
        若正文为空或只有空白，只返回 chunk_0。
    """
```

### 处理细节

- `content` 为 `None` 或纯空白时，只返回 `[Chunk(0, f"{title}\n{summary}", "summary")]`
- 正文分段后，逐段判断长度：
  - `len(paragraph) < min_size`：与下一段合并（累加到 buffer）
  - `len(paragraph) > max_size`：按 `re.split(r'[。？！]', paragraph)` 断开，每段 ≤ max_size
  - 正常段落直接作为一个 chunk
- 合并后的 buffer 在遇到正常段落或最后一段时 flush

### 配套测试

**文件**: `backend/tests/unit/domain/test_text_chunker.py`

| 测试用例 | 说明 |
|----------|------|
| `test_empty_content` | content 为空/None，只返回 chunk_0 |
| `test_title_summary_chunk` | chunk_0 始终是 title + summary |
| `test_short_paragraphs_merge` | 多个短段落合并为一个 chunk |
| `test_long_paragraph_split` | 超长段落按句号断开 |
| `test_normal_paragraphs` | 正常段落各自成为 chunk |
| `test_mixed_paragraphs` | 短+长+正常混合 |
| `test_chunk_index_sequential` | chunk index 连续递增 |

---

## Step 2: 新增合并去重函数 `search_result_merger.py`

**文件**: `backend/app/domain/services/search_result_merger.py`（新建）

三个检索消费方（retrieve、stock_news_analyst、`_find_related_analyses`）都需要将同一篇文章的多个 chunk 命中结果合并为一条。提取为公共函数。

### 函数签名

```python
from app.domain.entities.vector_search import VectorSearchResult

def merge_chunk_results(
    results: list[VectorSearchResult],
    max_articles: int = 3,
    max_content_length: int = 3000,
) -> list[dict]:
    """将多个 chunk 命中结果按 article_id 分组合并。

    Args:
        results: 向量检索返回的原始结果列表。
        max_articles: 最多返回的文章数量。
        max_content_length: 每篇文章拼接 content 的最大字符数。

    Returns:
        合并后的文章列表，每项包含：
        {
            "article_id": str,
            "title": str,
            "summary": str,
            "content": str,       # 多个 chunk 的 content 拼接
            "score": float,       # 最高分数
            "source": str,        # "vector_search"
        }

    向下兼容：旧格式 doc_id（无 `_chunk_` 后缀，如 `article_123`）
    也能正确处理，article_id 提取为完整 doc_id。
    """
```

### 处理逻辑

1. **article_id 提取**：
   - `doc_id` 含 `_chunk_` → 取 `_chunk_` 前面的部分（如 `article_123_chunk_2` → `article_123`）
   - `doc_id` 不含 `_chunk_` → 直接使用（向下兼容旧数据）
2. **按 article_id 分组**：
   - 同一文章：content 按 chunk_index 排序后拼接
   - summary 取 `chunk_type == "summary"` 的块内容
   - title 取 metadata 中的 title
   - score 取该文章所有 chunk 中的最高分
3. **按 score 降序排列**，截取 `max_articles` 篇
4. **每篇 content 截断**到 `max_content_length` 字符

### 配套测试

**文件**: `backend/tests/unit/domain/test_search_result_merger.py`

| 测试用例 | 说明 |
|----------|------|
| `test_empty_results` | 空列表返回空 |
| `test_single_article_single_chunk` | 单条结果原样返回 |
| `test_same_article_multiple_chunks` | 同一文章多个 chunk 合并 |
| `test_different_articles_sorted_by_score` | 多篇文章按 score 降序 |
| `test_max_articles_limit` | 超过 max_articles 时截断 |
| `test_content_truncation` | content 超长时截断 |
| `test_legacy_doc_id_compat` | 旧格式 doc_id（无 `_chunk_`）正确处理 |
| `test_summary_extraction` | summary 从 chunk_type="summary" 的块中提取 |

---

## Step 3: 扩展向量库接口 — 支持 `delete_by_filter`

### 3a. Domain 抽象接口

**文件**: `backend/app/domain/repositories/vector_search_repo.py`

新增抽象方法：

```python
async def delete_by_filter(self, collection: str, filters: dict) -> int:
    """按 metadata 条件批量删除文档，返回删除数量。"""
```

### 3b. ChromaStore 底层

**文件**: `backend/app/infrastructure/vector/chroma_store.py`

新增 `get_by_filter` 方法（delete_by_filter 的前置依赖，用于查到待删 ID）：

```python
def get_by_filter(
    self,
    collection_name: str,
    where: dict,
) -> list[dict]:
    """按 metadata 条件查询文档，返回 [{"id": ..., "metadata": ...}, ...]"""
    collection = self._get_or_create_collection(collection_name)
    results = collection.get(where=where)
    return [
        {"id": id_, "metadata": meta}
        for id_, meta in zip(results["ids"], results["metadatas"] or [])
    ]
```

> **注意**：当前 `ChromaVectorStore` 的 `delete()` 方法已支持 `ids: list[str]`，无需修改。

### 3c. Repository 实现

**文件**: `backend/app/infrastructure/repositories/chroma_vector_search_repo.py`

```python
async def delete_by_filter(self, collection: str, filters: dict) -> int:
    records = self.store.get_by_filter(collection, where=filters)
    if not records:
        return 0
    ids = [r["id"] for r in records]
    self.store.delete(collection, ids=ids)
    return len(ids)
```

### 配套测试

在现有 `tests/unit/test_vector_search_repo.py` 中新增测试用例：

| 测试用例 | 说明 |
|----------|------|
| `test_delete_by_filter_success` | 按 article_id 过滤删除，返回删除数量 |
| `test_delete_by_filter_no_match` | 过滤条件无匹配，返回 0 |

---

## Step 4: 改造存入/删除逻辑

**文件**: `backend/app/application/use_cases/manage_article.py`

### 4a. SaveArticleUseCase — chunk 化写入

**当前逻辑**（第 99-120 行）：

```python
embed_text = f"{saved.title}\n{saved.summary}"
embedding = await self.embedding_service.embed(embed_text)
await self.vector_search_repo.add(
    collection="knowledge_articles",
    doc_id=f"article_{saved.article_id}",
    embedding=embedding, metadata=metadata, document=embed_text,
)
```

**改为**：

```python
from app.domain.services.text_chunker import chunk_article

chunks = chunk_article(saved.title, saved.summary or "", saved.content or "")
texts = [c.content for c in chunks]
embeddings = await self.embedding_service.embed_batch(texts)

for chunk, embedding in zip(chunks, embeddings):
    chunk_metadata = {
        **base_metadata,  # user_id, title, stock_codes, industries, event_type
        "article_id": str(saved.article_id),
        "chunk_index": chunk.index,
        "chunk_type": chunk.chunk_type,
    }
    await self.vector_search_repo.add(
        collection="knowledge_articles",
        doc_id=f"article_{saved.article_id}_chunk_{chunk.index}",
        embedding=embedding,
        metadata=chunk_metadata,
        document=chunk.content,
    )
```

**metadata 新增字段**：
- `article_id`（原文章 ID，字符串形式）
- `chunk_index`（块序号，int）
- `chunk_type`（`"summary"` 或 `"content"`）

### 4b. DeleteArticleUseCase — 按过滤删除

**当前逻辑**（第 173-185 行）：

```python
await self.vector_search_repo.delete(
    collection="knowledge_articles",
    doc_id=f"article_{article_id}",
)
```

**改为**：

```python
await self.vector_search_repo.delete_by_filter(
    collection="knowledge_articles",
    filters={"article_id": str(article_id)},
)
```

---

## Step 5: 改造检索消费方

### 5a. retrieve 节点

**文件**: `backend/app/infrastructure/workflow/nodes/retrieve.py`

**改动要点**：
- `top_k` 从 `3` 调到 `6`（chunk 化后同一文章可能命中多个 chunk，需要多取）
- 调用 `merge_chunk_results(vector_results, max_articles=3)` 合并去重
- 替换当前的手动结果拼接逻辑
- 输出结构不变（`{"title", "summary", "content", "score", ...}`），下游无需改动

**伪代码**：

```python
from app.domain.services.search_result_merger import merge_chunk_results

# 向量检索
vector_results = await vector_search_repo.search(
    query_embedding=query_embedding,
    top_k=6,  # 从 3 → 6
    threshold=settings.rag_similarity_threshold,
    collection="knowledge_articles",
    filters={"user_id": user_id},
)

# 合并去重
merged = merge_chunk_results(vector_results, max_articles=3)

# 用 merged 替换当前的手动拼接逻辑
knowledge_context = format_merged_results(merged)
```

### 5b. stock_news_analyst 节点

**文件**: `backend/app/infrastructure/workflow/nodes/stock_news_analyst.py`

**改动要点**：
- `top_k` 从 `3` 调到 `6`
- 调用 `merge_chunk_results` 合并去重
- 拼接逻辑改为使用合并后的结果（已包含丰富 content）

**伪代码**：

```python
from app.domain.services.search_result_merger import merge_chunk_results

vector_results = await vector_search_repo.search(
    query_embedding=query_embedding,
    top_k=6,  # 从 3 → 6
    threshold=settings.rag_similarity_threshold,
    collection="knowledge_articles",
)

merged = merge_chunk_results(vector_results, max_articles=3)
# 用 merged 构建历史分析上下文
```

### 5c. `_find_related_analyses`

**文件**: `backend/app/application/use_cases/event_radar.py`（第 333-369 行）

**改动要点**：
- `top_k` 从 `3` 调到 `6`
- article_id 提取改为兼容 chunk 格式：`raw_id.split("_chunk_")[0]`
- 调用 `merge_chunk_results` 合并去重
- 替换当前的手动结果转换逻辑

**伪代码**：

```python
from app.domain.services.search_result_merger import merge_chunk_results

vector_results = await self.vector_search_repo.search(
    query_embedding=query_embedding,
    top_k=6,  # 从 3 → 6
    threshold=settings.rag_similarity_threshold,
    collection="knowledge_articles",
)

merged = merge_chunk_results(vector_results, max_articles=3)

# 将 merged 转换为 RelatedAnalysis 列表
related = [
    RelatedAnalysis(
        article_id=int(item["article_id"].replace("article_", "")),
        title=item["title"],
        summary=item["summary"],
        relevance_score=item["score"],
    )
    for item in merged
]
```

---

## Step 6: 改造重建脚本

**文件**: `backend/scripts/rebuild_vector_index.py`

**改动要点**：

1. **SQL 查询增加 `content` 字段**：
   ```python
   # 当前：SELECT article_id, title, summary, ...
   # 改为：SELECT article_id, title, summary, content, ...
   ```

2. **先删除旧集合再写入**：
   ```python
   # 重建 knowledge_articles 时，先清除旧数据
   chroma_store.delete_collection("knowledge_articles")
   chroma_store._get_or_create_collection("knowledge_articles")
   ```

3. **使用 `chunk_article` 切分后批量写入**：
   ```python
   from app.domain.services.text_chunker import chunk_article

   for article in articles:
       chunks = chunk_article(
           article.title, article.summary or "", article.content or ""
       )
       texts = [c.content for c in chunks]
       embeddings = await embedding_svc.embed_batch(texts)

       for chunk, embedding in zip(chunks, embeddings):
           metadata = {
               "user_id": str(article.user_id),
               "title": article.title,
               "article_id": str(article.article_id),
               "chunk_index": chunk.index,
               "chunk_type": chunk.chunk_type,
               "stock_codes": ",".join(...),
               "industries": ",".join(...),
               "event_type": article.event_type or "",
           }
           doc_id = f"article_{article.article_id}_chunk_{chunk.index}"
           await vector_repo.add(
               collection="knowledge_articles",
               doc_id=doc_id,
               embedding=embedding,
               metadata=metadata,
               document=chunk.content,
           )
   ```

4. **进度日志增强**：显示 chunk 数量而非文章数量

> **注意**：`impact_events` 部分保持不变，不做分块。

---

## Step 7: 测试验证

### 单元测试

| 测试文件 | 用例数 | 覆盖范围 |
|----------|--------|----------|
| `tests/unit/domain/test_text_chunker.py` | 7 | 空内容、标题摘要块、短段落合并、长段落拆分、正常段落、混合场景、index 连续性 |
| `tests/unit/domain/test_search_result_merger.py` | 8 | 空结果、单条、同文章多 chunk、多文章排序、数量限制、内容截断、旧格式兼容、summary 提取 |
| `tests/unit/test_vector_search_repo.py`（扩展） | 2 | delete_by_filter 成功/无匹配 |

### 集成验证步骤

```bash
# 1. 重建 knowledge_articles 集合
python -m scripts.rebuild_vector_index --collection knowledge_articles

# 2. 确认 chunk 化成功（文档数 > 文章数）
python -m scripts.query_vector_db status

# 3. 搜索验证正文级命中
python -m scripts.query_vector_db search "德业股份"

# 4. 端到端验证：重启服务，输入"分析德业股份"
#    检查日志中 retrieve 节点的检索结果包含正文内容
```

---

## 向下兼容性

| 维度 | 说明 |
|------|------|
| **旧数据** | `merge_chunk_results` 能正确处理无 `_chunk_` 后缀的旧 doc_id，无需强制迁移 |
| **检索结果结构** | 输出仍为 `{"title", "summary", "content", "score", ...}`，下游消费逻辑不变 |
| **impact_events** | 不受影响，不做分块 |
| **重建脚本** | 重建后旧数据被覆盖，需先清空 `knowledge_articles` 集合再写入 |
| **API 契约** | 前端零改动，所有变更后端内部消化 |

---

## 风险与应对

| 风险 | 影响 | 应对 |
|------|------|------|
| ChromaDB 文档数膨胀（1 篇文章 → ~5 个 chunk） | 存储和检索略增 | ChromaDB 嵌入式设计支持万级文档，数百文章 × 5 chunk 仍远低于阈值 |
| 批量 embed 性能 | 首次重建耗时增加 | 已有 `embed_batch` 批量接口，每批 32 条 |
| 旧数据残留 | 重建前旧格式 doc_id 未清理 | 重建脚本先删集合再写入 |
| 检索 top_k 增大后延迟 | 从 3 → 6，延迟微增 | ChromaDB HNSW 索引在万级数据下差异可忽略 |
