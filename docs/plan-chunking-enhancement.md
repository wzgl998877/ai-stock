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

### 背景：content 的实际格式

文章 content 由 LLM 流式生成，存储为 **Markdown 格式**，使用 `##` 二级标题划分章节。
典型结构：

```markdown
## 事件背景
正文内容...

## 影响逻辑
正文内容...

## 受益行业
正文内容...

## 受损行业
正文内容...

## 推荐关注股票
正文内容...

## 风险提示
正文内容...
```

> 参见 `backend/app/infrastructure/ai/prompts/policy.py` 等 prompt 模板，
> LLM 被指示按 `##` 章节输出分析报告。

### 切分策略——Markdown 章节级切分

以 `##` 标题为边界进行切分，每个章节（含标题 + 正文 + 表格）作为独立 chunk。

**为什么不按 `\n\n` 分段？**

`content.split("\n\n")` 会把 `## 事件背景`（6 字）和它下面的正文拆散，
导致标题变成"短段落"触发合并逻辑，不同章节的内容被混在一起。
Markdown 表格（`| ... |` 多行）也会被 `\n\n` 切碎。
按 `##` 章节切分天然保证语义完整性。

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
import re

def chunk_article(
    title: str,
    summary: str,
    content: str,
    max_size: int = 1500,
) -> list[Chunk]:
    """将文章按 Markdown ## 章节切分为语义 chunk 列表。

    切分规则：
        - chunk_0 始终是 title + summary（保留标题级匹配能力）
        - content 按 ## 标题分段，每个章节作为一个独立 chunk
        - 超过 max_size 的章节按 \\n\\n 段落二次拆分

    Args:
        title: 文章标题
        summary: 文章摘要
        content: Markdown 格式正文（由 LLM 生成，含 ## 章节结构）
        max_size: 单个 chunk 最大字符数，默认 1500

    Returns:
        始终返回至少一个 Chunk（chunk_0 = title + summary）。
        若正文为空或只有空白，只返回 chunk_0。
    """
```

### 算法伪代码

```
输入: title, summary, content, max_size=1500
输出: list[Chunk]

━━━ 第一步：生成 chunk_0（标题 + 摘要块）━━━

chunks = [Chunk(index=0, content=f"{title}\n{summary}", chunk_type="summary")]

如果 content 为 None 或去除空白后为空:
    直接返回 chunks

━━━ 第二步：按 ## 标题分段 ━━━

sections = re.split(r'(?=^## )', content, flags=re.MULTILINE)
# 结果示例：
# ["", "## 事件背景\n正文...", "## 影响逻辑\n正文...", "## 风险提示\n正文..."]
sections = [s.strip() for s in sections if s.strip()]

chunk_index = 1

for section in sections:
    如果 len(section) <= max_size:
        # 章节长度合适，直接作为一个 chunk
        chunks.append(Chunk(index=chunk_index, content=section, chunk_type="content"))
        chunk_index += 1

    否则:
        # 章节超长（如含大型 Markdown 表格），按段落二次拆分
        paragraphs = section.split("\n\n")
        buffer = ""

        for para in paragraphs:
            merged = buffer + "\n\n" + para if buffer else para

            如果 len(merged) <= max_size:
                buffer = merged
            否则:
                如果 buffer:
                    chunks.append(Chunk(index=chunk_index, content=buffer, chunk_type="content"))
                    chunk_index += 1
                buffer = para

        如果 buffer:
            chunks.append(Chunk(index=chunk_index, content=buffer, chunk_type="content"))
            chunk_index += 1

返回 chunks
```

### max_size 参数说明

| 参数 | 值 | 理由 |
|------|-----|------|
| `max_size` | 1500 | bge-large-zh-v1.5 最大 512 tokens，1500 字中文约 500-700 tokens，在模型窗口内且留有余量 |
| 不设 `min_size` | - | `##` 章节级切分已保证语义完整性，不需要短段合并 |

### 切分结果示例

输入（3544 字的真实文章）：

> **title**: 光储融合与技术迭代驱动的产业链传导
>
> **summary**: 传导起于电力设备，光储融合与新技术迭代主要受益电力设备及机械设备，受损煤炭。最大风险为海外贸易壁垒及产能过剩导致价格战。
>
> **content**: *(含 7 个 ## 章节的 Markdown)*

执行 `chunk_article(title, summary, content)` 后输出 **8 个 Chunk**：

| Chunk | chunk_type | 内容 | 长度 |
|-------|-----------|------|------|
| 0 | summary | `title + "\n" + summary` | ~75 字 |
| 1 | content | `## 事件背景` + 正文 | ~130 字 |
| 2 | content | `## 影响逻辑` + 正文 | ~130 字 |
| 3 | content | `## 产业链传导表` + Markdown 表格 | ~530 字 |
| 4 | content | `## 受益行业` + 正文 | ~150 字 |
| 5 | content | `## 受损行业` + 正文 | ~80 字 |
| 6 | content | `## 推荐关注股票` + 列表 | ~130 字 |
| 7 | content | `## 风险提示` + 正文 | ~160 字 |

每个 chunk 是一个语义完整的章节，包含标题 + 正文 + 表格。
对于超长章节（如某篇文章的"新闻分析"章节含 5000+ 字数据表格），
触发二次拆分，在该章节内部按 `\n\n` 分段合并，确保每个子 chunk ≤ max_size。

### 与原方案的核心区别

| 维度 | 原方案（按 `\n\n` 分段） | 新方案（按 `##` 章节） |
|------|--------------------------|----------------------|
| 切分边界 | 双换行符 | Markdown `##` 标题 |
| 语义完整性 | 差，标题和正文会被拆散 | 好，每个 chunk 是完整章节 |
| 短段合并 | 需要复杂的 min_size/buffer 逻辑 | 不需要，章节已保证完整 |
| 表格处理 | 差，Markdown 表格被切碎 | 好，表格属于章节内部不会被拆 |
| 参数复杂度 | min_size + max_size + buffer | 只需 max_size |
| 平均 chunk 数 | 难以预估 | 与章节数一致，~6-8 个 |

### 配套测试

**文件**: `backend/tests/unit/domain/test_text_chunker.py`

| 测试用例 | 说明 |
|----------|------|
| `test_empty_content` | content 为空/None，只返回 chunk_0 |
| `test_title_summary_chunk` | chunk_0 始终是 `title + "\n" + summary`，chunk_type="summary" |
| `test_single_section` | 只有一个 `##` 章节，返回 chunk_0 + chunk_1 |
| `test_multiple_sections` | 多个 `##` 章节各自成为独立 chunk |
| `test_section_with_table` | 包含 Markdown 表格的章节不被拆散 |
| `test_oversized_section_split` | 超过 max_size 的章节按段落二次拆分 |
| `test_content_without_headers` | content 无 `##` 标题但有正文，整体作为一个 chunk |
| `test_chunk_index_sequential` | chunk index 从 0 开始连续递增 |
| `test_mixed_h2_h3` | `##` 和 `###` 混合时只按 `##` 切分，`###` 保留在章节内 |

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
| `tests/unit/domain/test_text_chunker.py` | 9 | 空内容、标题摘要块、单章节、多章节、含表格、超长章节二次拆分、无标题正文、index 连续性、h2/h3 混合 |
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
| ChromaDB 文档数膨胀（1 篇文章 → ~6-8 个 chunk） | 存储和检索略增 | ChromaDB 嵌入式设计支持万级文档，数百文章 × 7 chunk 仍远低于阈值 |
| 批量 embed 性能 | 首次重建耗时增加 | 已有 `embed_batch` 批量接口，每批 32 条 |
| 旧数据残留 | 重建前旧格式 doc_id 未清理 | 重建脚本先删集合再写入 |
| 检索 top_k 增大后延迟 | 从 3 → 6，延迟微增 | ChromaDB HNSW 索引在万级数据下差异可忽略 |
