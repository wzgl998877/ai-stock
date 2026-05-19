# Research: RAG 语义检索增强

**Feature**: 008-rag-semantic-retrieval
**Date**: 2026-05-19

## R1: Embedding 模型选型

**Decision**: `BAAI/bge-large-zh-v1.5`

**Rationale**:
- 中文语义检索 benchmark（C-MTEB）排名第一梯队
- 1024 维向量，精度和性能平衡
- 本地推理无需 API 费用，CPU 可运行
- sentence-transformers 原生支持，API 简洁

**Alternatives considered**:
- `m3e-base`（768 维）：轻量但精度低于 bge-large
- `text-embedding-3-small`（OpenAI API）：精度高但需外部 API，有成本和数据隐私问题
- `bge-small-zh`（512 维）：更快但精度牺牲较大

## R2: 向量数据库选型

**Decision**: ChromaDB（嵌入式 PersistentClient）

**Rationale**:
- Python 原生，与 FastAPI 同进程，零运维
- 数据量 < 10,000 篇，ChromaDB 性能完全够用
- 支持 metadata 过滤（按行业、股票代码筛选）
- 本地文件存储，无需独立服务

**Alternatives considered**:
- Qdrant：功能更强但需 Docker 部署额外服务，当前数据量不需要
- FAISS：纯索引库，缺少 metadata 过滤和 CRUD 管理
- pgvector：需 PostgreSQL，与现有 MySQL 架构不一致

## R3: Retrieve 节点改造策略

**Decision**: 完全替换，无结果时回退 FULLTEXT

**Rationale**:
- 当前 retrieve 节点直接硬编码 `MySQLSearchRepository`，无抽象层
- 改造方式：在 `create_retrieve_node` 闭包中注入 `VectorSearchRepository`，优先向量检索
- 回退逻辑：向量返回空列表时，调用原有 `MySQLSearchRepository` 兜底
- 输入输出接口不变（`AnalysisState.search_results`），下游 `summarize_context` 无感知

**Implementation detail**:
```
retrieve_node(state):
  query = state["raw_text"][:80]
  # 1. 尝试向量检索
  results = vector_repo.search(query_embedding, top_k=3, user_id=user_id)
  if not results:
    # 2. 回退 FULLTEXT
    results = mysql_search_repo.search(query, user_id, page=1, page_size=3)
  # 3. 格式化输出（与现有格式一致）
  return {"search_results": formatted_results}
```

## R4: Embedding 生成时机

**Decision**: 文章保存时同步生成标题+摘要 embedding，异步生成正文 embedding

**Rationale**:
- 标题+摘要文本短（< 200 字），embedding 生成 < 100ms，同步不影响保存体验
- 正文可能很长（数千字），embedding 生成耗时较长，异步处理避免阻塞
- retrieve 节点主要用标题+摘要 embedding 检索，正文 embedding 用于精准场景（事件关联）
- 事件入库时同步生成（标题+摘要，文本短）

## R5: 事件去重增强策略

**Decision**: 在现有 URL hash → Jaccard 链路后，新增语义 embedding 相似度作为第三层

**Rationale**:
- 现有 `event_dedup.py` 用 URL hash（精确）+ 字符级 Jaccard（模糊）
- Jaccard 基于字符集重叠，对"央行降息 25 个基点" vs "人民银行下调基准利率 0.25%"识别力弱
- 语义 embedding 能捕捉同义表达，阈值设 0.85（比检索更严格）
- 执行顺序保持不变：URL hash（最快）→ Jaccard（快）→ embedding（较慢但最准）
- 如果前两层已判定重复，跳过 embedding 计算节省性能

## R6: ChromaDB 集合设计

**Decision**: 两个独立集合

**Rationale**:
- `knowledge_articles`: 知识库文章，embedding 用标题+摘要拼接
  - metadata: `user_id`, `title`, `stock_codes`(逗号分隔), `industries`(逗号分隔), `event_type`
- `impact_events`: 影响事件，embedding 用标题+摘要拼接
  - metadata: `title`, `affected_stocks`(逗号分隔), `affected_industries`(逗号分隔)
- 分开集合而非混合：查询场景不同（文章检索 vs 事件关联 vs 事件去重），metadata 结构不同
- 每个集合数据量小（< 10K），ChromaDB 单集合查询性能优秀

## R7: 降级与容错策略

**Decision**: 全局 RAG 开关 + 每次检索独立 try-catch

**Rationale**:
- `RAG_ENABLED` 配置项：全局开关，关闭时所有场景直接走 FULLTEXT
- 每个 retrieve/search 调用独立 try-except：单次 embedding 失败不影响其他
- 模型加载失败：启动时日志告警，`embedding_service.is_ready()` 返回 False，所有检索自动降级
- ChromaDB 写入失败：日志记录，不阻塞主流程（MySQL 优先）
- ChromaDB 数据损坏：提供重建脚本，从 MySQL 全量重新生成 embedding

## R8: 依赖版本兼容性

**Decision**: sentence-transformers >= 2.2.0, chromadb >= 0.4.0

**Rationale**:
- sentence-transformers 2.2+ 支持 bge 系列模型
- chromadb 0.4+ 支持 PersistentClient 和 async-compatible 操作
- 两者都是纯 Python 包，与现有 Python 3.x + FastAPI 环境兼容
- chromadb 依赖 onnxruntime，CPU 推理自动使用 ONNX 后端，无需手动配置
- 模型文件首次自动下载到 `~/.cache/huggingface/`，后续本地缓存

## R9: 数据灌入向量库的完整流程

**Decision**: 在 3 个入口点（文章保存、事件入库、文章更新）生成 embedding 并写入 ChromaDB，通过 Application 层用例编排调用链。

### 9.1 文章保存时写入向量库

**调用链**（改造 `SaveArticleUseCase` + `analysis.py` 路由）：

```
Router (analysis.py)
  │
  │  从 request.app.state 获取 embedding_service / vector_search_repo
  │
  ▼
SaveArticleUseCase.__init__(article_repo, industry_repo, vector_search_repo=None, embedding_service=None)
  │
  ▼
SaveArticleUseCase.execute(title, summary, content, ...)
  │
  ├─ 1. [现有] 验证 content 非空，降级 summary
  ├─ 2. [现有] 解析 industry_codes → resolved_codes
  ├─ 3. [现有] 构建 Article 实体
  ├─ 4. [现有] article_repo.save(article) → MySQL INSERT → 返回 saved（含 article_id）
  │
  ├─ 5. [新增] 生成 embedding 并写入 ChromaDB（仅当 vector_search_repo 和 embedding_service 可用时）
  │     │
  │     ├─ if not embedding_service.is_ready(): 跳过，日志告警
  │     │
  │     ├─ 构建嵌入文本: embed_text = f"{title}\n{summary}"
  │     │
  │     ├─ embedding = await embedding_service.embed(embed_text)
  │     │
  │     ├─ 构建元数据:
  │     │   metadata = {
  │     │     "user_id": saved.user_id,
  │     │     "title": saved.title,
  │     │     "stock_codes": ",".join(s.stock_code for s in saved.stocks),
  │     │     "industries": ",".join(i.industry_code for i in saved.industries),
  │     │     "event_type": saved.event_type,
  │     │   }
  │     │
  │     ├─ await vector_search_repo.add(
  │     │     collection="knowledge_articles",
  │     │     doc_id=f"article_{saved.article_id}",
  │     │     embedding=embedding,
  │     │     metadata=metadata,
  │     │     document=embed_text,
  │     │   )
  │     │
  │     └─ try-except 包裹：失败时 logger.warning，不阻塞返回 saved
  │
  └─ 6. 返回 saved（无论 embedding 是否成功）
```

**关键设计**：
- embedding 生成在 `article_repo.save()` **之后**，因为需要 `saved.article_id`
- 标题+摘要拼接用 `\n` 分隔，与检索时 query 的编码方式一致
- metadata 中 stock_codes/industries 用逗号分隔字符串，支持 ChromaDB metadata 过滤
- 整个 embedding + 写入 ChromaDB 步骤在 try-except 中，失败不影响文章保存

### 9.2 事件入库时写入向量库

**调用链**（改造 `EventRadarUseCase.crawl_and_process()`）：

```
EventRadarUseCase.__init__(..., vector_search_repo=None, embedding_service=None)
  │
  ▼
crawl_and_process()
  │
  ├─ 1. [现有] ClsProvider().fetch_latest(limit=50)
  ├─ 2. [现有] 遍历 articles，对每条执行 assess_event()（去重 + 影响判断）
  │
  │  对于通过去重的新事件：
  │
  ├─ 3. [现有] event = ImpactEvent(...)
  ├─ 4. [现有] event = await event_repo.create(event)  → MySQL INSERT → 返回含 event_id
  │
  ├─ 5. [新增] 生成事件 embedding 并写入 ChromaDB
  │     │
  │     ├─ if embedding_service and embedding_service.is_ready():
  │     │
  │     ├─ embed_text = f"{event.title}\n{event.summary or ''}"
  │     │
  │     ├─ embedding = await embedding_service.embed(embed_text)
  │     │
  │     ├─ metadata = {
  │     │     "title": event.title,
  │     │     "affected_stocks": ",".join(s.get("code","") for s in (event.affected_stocks or [])),
  │     │     "affected_industries": ",".join(i.get("code","") for i in (event.affected_industries or [])),
  │     │     "sentiment": event.sentiment or "neutral",
  │     │   }
  │     │
  │     ├─ await vector_search_repo.add(
  │     │     collection="impact_events",
  │     │     doc_id=f"event_{event.event_id}",
  │     │     embedding=embedding,
  │     │     metadata=metadata,
  │     │     document=embed_text,
  │     │   )
  │     │
  │     └─ try-except：失败时 logger.warning，不阻塞采集流程
  │
  ├─ 6. [现有] article_repo.create(impact_article)
  ├─ 7. [现有] _match_users_for_events(new_events)
  │
  └─ 8. 返回 {"crawled": N, "new_events": M}
```

**关键设计**：
- embedding 在 `event_repo.create()` 之后生成（需要 event_id）
- 事件标题+摘要是核心嵌入文本，与文章一致
- 事件采集是定时批量任务，每条约增加 50-100ms（embedding 生成），50 条约 2.5-5s 增量
- 失败不阻塞采集流程，日志记录后继续处理下一条

### 9.3 文章更新时覆盖向量

**调用链**（需在 `SaveArticleUseCase` 或独立 `UpdateArticleUseCase` 中处理）：

当前代码没有显式的"更新文章"用例（文章保存后不修改），但 FR-011 要求支持更新场景。

**方案**：在 `SaveArticleUseCase` 中增加 `update` 方法，或在 Router 层检测重复 article_id 时调用 update：

```
SaveArticleUseCase.update(article_id, title, summary, ...)
  │
  ├─ 1. article_repo.update(article) → MySQL UPDATE
  │
  ├─ 2. if embedding_service.is_ready():
  │     ├─ embed_text = f"{title}\n{summary}"
  │     ├─ new_embedding = await embedding_service.embed(embed_text)
  │     ├─ await vector_search_repo.update(
  │     │     collection="knowledge_articles",
  │     │     doc_id=f"article_{article_id}",
  │     │     embedding=new_embedding,
  │     │     metadata=new_metadata,
  │     │   )
  │     └─ try-except: 失败日志告警
  │
  └─ 3. 返回 updated article
```

**注意**：MVP 阶段文章保存后不修改，此流程可在 P4 之后实现。FR-011 要求覆盖能力存在，但 FR-010 保证保存优先。

### 9.4 文章删除时清理向量

**调用链**（改造 `DeleteArticleUseCase`）：

```
DeleteArticleUseCase.execute(article_id)
  │
  ├─ 1. [现有] article_repo.delete(article_id) → MySQL 软删除
  │
  ├─ 2. [新增] if vector_search_repo:
  │     ├─ await vector_search_repo.delete(
  │     │     collection="knowledge_articles",
  │     │     doc_id=f"article_{article_id}",
  │     │   )
  │     └─ try-except: 失败日志告警（向量残留不影响业务，可通过重建脚本修复）
  │
  └─ 3. 返回 True
```

### 9.5 服务初始化（main.py lifespan 改造）

**调用链**（改造 `main.py` 的 `lifespan()` 函数）：

```
lifespan(app):
  │
  ├─ [现有] AIService 初始化
  ├─ [现有] SearchService 初始化
  │
  ├─ [新增] Embedding 服务初始化
  │     │
  │     ├─ from app.infrastructure.vector.embedding_client import LocalEmbeddingService
  │     ├─ from app.infrastructure.vector.chroma_store import ChromaVectorStore
  │     ├─ from app.infrastructure.repositories.chroma_vector_search_repo import ChromaVectorSearchRepo
  │     │
  │     ├─ if settings.RAG_ENABLED:
  │     │     embedding_service = LocalEmbeddingService(model_name=settings.RAG_EMBEDDING_MODEL)
  │     │     chroma_store = ChromaVectorStore(persist_dir=settings.RAG_VECTOR_DB_PATH)
  │     │     vector_search_repo = ChromaVectorSearchRepo(chroma_store)
  │     │     logger.info("RAG 初始化完成: model=%s, db=%s", settings.RAG_EMBEDDING_MODEL, settings.RAG_VECTOR_DB_PATH)
  │     │ else:
  │     │     embedding_service = None
  │     │     vector_search_repo = None
  │     │
  │     └─ app.state.embedding_service = embedding_service
  │        app.state.vector_search_repo = vector_search_repo
  │
  ├─ [改造] build_analysis_graph() 注入 vector_search_repo + embedding_service
  │     analysis_graph = build_analysis_graph(
  │         session_factory=async_session,
  │         ai_service=app.state.ai_service,
  │         search_service=_search_svc,
  │         vector_search_repo=vector_search_repo,    # 新增
  │         embedding_service=embedding_service,      # 新增
  │     )
  │
  ├─ [改造] 事件采集调度器注入 vector_search_repo + embedding_service
  │     _event_scheduler = setup_scheduler(
  │         session_factory=async_session,
  │         ai_service=app.state.ai_service,
  │         search_service=_search_svc,
  │         vector_search_repo=vector_search_repo,    # 新增
  │         embedding_service=embedding_service,      # 新增
  │     )
  │
  └─ [现有] 个股分析图、残留任务清理、股票名称映射等...
```

### 9.6 路由层注入方式

**改造 `analysis.py` Router**：

```python
# 现有
article_repo = MySQLArticleRepository(db)
industry_repo = MySQLIndustryRepository(db)
use_case = SaveArticleUseCase(article_repo, industry_repo)

# 改造后
article_repo = MySQLArticleRepository(db)
industry_repo = MySQLIndustryRepository(db)
embedding_svc = request.app.state.embedding_service   # 从 app.state 获取
vector_repo = request.app.state.vector_search_repo    # 从 app.state 获取
use_case = SaveArticleUseCase(article_repo, industry_repo, vector_repo, embedding_svc)
```

### 9.7 向量重建脚本（运维工具）

提供 CLI 脚本从 MySQL 全量重建 ChromaDB 索引（应对数据损坏）：

```
scripts/rebuild_vector_index.py
  │
  ├─ 遍历 t_analysis_article（status='completed', deleted='0'）
  │     → 批量 embed(title + summary) → 写入 knowledge_articles
  │
  ├─ 遍历 t_impact_event
  │     → 批量 embed(title + summary) → 写入 impact_events
  │
  └─ 使用 embed_batch() 批量处理，每批 32 条
```

**Rationale**:
- 完整的数据灌入流程覆盖了 FR-001（文章 embedding）、FR-002（事件 embedding）、FR-010（不阻塞保存）、FR-011（覆盖更新）
- Application 层用例编排调用链，符合 Router → Application → Domain → Infrastructure 分层
- 通过 `app.state` 在 lifespan 中初始化并注入，与现有 `ai_service`、`search_service` 模式一致
- 所有 embedding 操作包裹在 try-except 中，保证主流程不中断
