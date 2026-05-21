# 实现 Parent-Child 扩展检索（Auto-Merging）

## Context

当前 `merge_chunk_results` 只合并检索命中的 chunk。如果检索只命中某篇文章的摘要块（chunk_0），content 拼接结果为空，LLM 拿不到正文。

**解决方案**：在 `merge_chunk_results` 内部增加一步扩展逻辑——当某篇文章的 content 不足时，按 `article_id` 从 ChromaDB 拉取该文章的所有 chunk 补充内容。

---

## 改动范围

### Step 1: ChromaStore 新增 `get_by_filter_with_content`

**文件**: `backend/app/infrastructure/vector/chroma_store.py`

已有 `get_by_filter` 返回 `{"id": ..., "metadata": ...}`，需要同时返回 `document` 字段（即 chunk 正文）。

新增方法或扩展现有方法，返回包含 document 的完整记录。

### Step 2: 扩展 `merge_chunk_results` 支持扩展函数

**文件**: `backend/app/domain/services/search_result_merger.py`

在 `merge_chunk_results` 函数签名中增加可选参数 `expand_fn`：

```python
async def merge_chunk_results(
    results: list[VectorSearchResult],
    max_articles: int = 3,
    max_content_length: int = 3000,
    expand_fn: Callable[[str], list[VectorSearchResult]] | None = None,
) -> list[dict]:
```

- `expand_fn(article_id)` 是一个异步回调，接收 article_id，返回该文章的所有 chunk 结果
- 在合并过程中，如果某篇文章的 content 为空或太短（< 200 字），调用 `expand_fn` 拉取完整内容
- 如果 `expand_fn` 为 None（向后兼容），行为不变

### Step 3: 三个消费方传入 expand_fn

**文件**: `retrieve.py`, `stock_news_analyst.py`, `event_radar.py`

在调用 `merge_chunk_results` 时，传入一个 `expand_fn` 回调，调用 `vector_search_repo.get_by_filter` 拉取该文章的所有 chunk，并包装为 `VectorSearchResult` 列表。

### Step 4: 单元测试

**文件**: `tests/unit/domain/test_search_result_merger.py` — 扩展

新增 2 个用例：
- `test_expand_fn_called_when_content_insufficient` — content 不足时调用 expand_fn
- `test_expand_fn_not_called_when_content_sufficient` — content 足够时不调用 expand_fn

---

## 关键文件清单

| 文件 | 操作 |
|------|------|
| `backend/app/infrastructure/vector/chroma_store.py` | 修改 — 新增 `get_by_filter` 返回 document |
| `backend/app/infrastructure/repositories/chroma_vector_search_repo.py` | 修改 — 新增 `get_by_filter` 返回 VectorSearchResult |
| `backend/app/domain/repositories/vector_search_repo.py` | 修改 — 新增 `get_by_filter` 抽象方法 |
| `backend/app/domain/services/search_result_merger.py` | 修改 — 新增 `expand_fn` 参数 |
| `backend/app/infrastructure/workflow/nodes/retrieve.py` | 修改 — 传入 expand_fn |
| `backend/app/infrastructure/workflow/nodes/stock_news_analyst.py` | 修改 — 传入 expand_fn |
| `backend/app/application/use_cases/event_radar.py` | 修改 — 传入 expand_fn |
| `backend/tests/unit/domain/test_search_result_merger.py` | 修改 — 新增 2 个用例 |

---

## 验证方式

```bash
cd backend && python -m pytest tests/unit/domain/test_search_result_merger.py -v
```

端到端：重启服务，输入"分析德业股份"，检查日志中 retrieve 节点的 content 是否包含正文内容。
