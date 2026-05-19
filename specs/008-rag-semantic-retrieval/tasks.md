# Tasks: RAG 语义检索增强

**Input**: Design documents from `/specs/008-rag-semantic-retrieval/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: 单元测试为强制要求（CLAUDE.md 规定），每个核心组件必须包含对应测试。

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (配置与依赖)

**Purpose**: 添加 RAG 所需的配置项和依赖包

- [x] T001 在 `backend/app/core/config.py` 的 Settings 类中新增 RAG 配置项：`RAG_ENABLED`(bool, True)、`RAG_EMBEDDING_MODEL`(str, "BAAI/bge-large-zh-v1.5")、`RAG_VECTOR_DB_PATH`(str, "./data/vector_db")、`RAG_SIMILARITY_THRESHOLD`(float, 0.7)、`RAG_DEDUP_THRESHOLD`(float, 0.85)、`RAG_MAX_CONTEXT_LENGTH`(int, 2000)
- [x] T002 在 `backend/requirements.txt` 中新增 `sentence-transformers>=2.2.0` 和 `chromadb>=0.4.0` 依赖

---

## Phase 2: Foundational (基础设施 — 阻塞所有 User Story)

**Purpose**: 所有 User Story 共享的 Domain 层抽象 + Infrastructure 层实现 + 服务初始化

**⚠️ CRITICAL**: 必须在本阶段完成后，才能开始任何 User Story 的实现

- [x] T003 [P] 创建向量检索领域实体 `backend/app/domain/entities/vector_search.py`，定义 `VectorSearchResult`（doc_id, score, metadata, document）和 `EmbeddingData`（doc_id, embedding, metadata, document）两个 dataclass
- [x] T004 [P] 创建向量检索仓储抽象接口 `backend/app/domain/repositories/vector_search_repo.py`，定义 `VectorSearchRepository` ABC，包含 `search`、`add`、`delete`、`update` 四个抽象方法，签名参照 contracts/vector-search-interface.md
- [x] T005 [P] 创建 Embedding 服务抽象接口 `backend/app/domain/services/embedding_service.py`，定义 `EmbeddingService` ABC，包含 `is_ready`、`embed`、`embed_batch` 三个抽象方法
- [x] T006 [P] 创建向量基础设施目录 `backend/app/infrastructure/vector/__init__.py`
- [x] T007 实现 Embedding 客户端 `backend/app/infrastructure/vector/embedding_client.py`，`LocalEmbeddingService` 类：构造函数加载 sentence-transformers 模型（BAAI/bge-large-zh-v1.5），实现 `is_ready()`（返回模型是否加载成功）、`embed()`（单条文本 → 1024 维向量）、`embed_batch()`（批量文本 → 向量列表）。加载失败时 `is_ready()` 返回 False，不抛异常，日志 WARNING
- [x] T008 实现 ChromaDB 存储封装 `backend/app/infrastructure/vector/chroma_store.py`，`ChromaVectorStore` 类：封装 `chromadb.PersistentClient`，提供 `get_or_create_collection(name)`、`add_documents(collection, ids, embeddings, metadatas, documents)`、`query(collection, query_embedding, top_k, filter, threshold)`、`delete(collection, ids)`、`update(collection, id, embedding, metadata)` 方法。threshold 过滤在 query 结果后按 distance/cosine 过滤
- [x] T009 实现向量检索仓储 `backend/app/infrastructure/repositories/chroma_vector_search_repo.py`，`ChromaVectorSearchRepo` 类继承 `VectorSearchRepository`，内部委托 `ChromaVectorStore` 完成实际操作。search 方法支持 collection 参数切换 knowledge_articles / impact_events 集合
- [x] T010 [P] 单元测试 Embedding 客户端 `backend/tests/unit/infrastructure/test_embedding_client.py`：测试 is_ready（成功/失败场景）、embed 返回 1024 维向量、embed_batch 批量返回、embed 空文本处理、模型加载失败降级
- [x] T011 [P] 单元测试 ChromaDB 存储 `backend/tests/unit/infrastructure/test_chroma_store.py`：测试 collection 创建、add_documents 写入、query 语义检索（用 mock 向量验证 threshold 过滤）、delete 删除、update 更新。使用 ChromaDB 内存模式（EphemeralClient）避免文件依赖
- [x] T012 [P] 单元测试向量检索仓储 `backend/tests/unit/infrastructure/test_vector_search_repo.py`：测试 search/add/delete/update 四个方法的完整流程，验证 metadata 过滤和 threshold 过滤行为
- [x] T013 改造 `backend/app/main.py` lifespan 函数：在 SearchService 初始化之后、LangGraph 图构建之前，新增 Embedding 服务初始化块——当 `settings.RAG_ENABLED` 时实例化 `LocalEmbeddingService`、`ChromaVectorStore`、`ChromaVectorSearchRepo`，存入 `app.state.embedding_service` 和 `app.state.vector_search_repo`；将两者作为新参数传入 `build_analysis_graph()` 和 `setup_scheduler()`。初始化失败时日志 WARNING，设为 None，不阻塞启动

**Checkpoint**: 基础设施就绪 — Embedding 服务和 ChromaDB 可用，User Story 实现可以开始

---

## Phase 3: User Story 1 - 事件分析上下文检索增强 (Priority: P1) 🎯 MVP

**Goal**: LangGraph retrieve 节点从 FULLTEXT 关键词检索升级为语义向量检索，无结果时自动回退 FULLTEXT。文章保存时自动生成 embedding 写入 ChromaDB。

**Independent Test**: 触发一次事件分析（输入"国际油价突破 85 美元"），验证 retrieve 节点返回的 top 3 历史文章语义相关性。关闭 RAG_ENABLED=false 后验证自动降级到 FULLTEXT。

### Implementation for User Story 1

- [x] T014 [US1] 改造 `backend/app/application/use_cases/manage_article.py` 的 `SaveArticleUseCase`：构造函数新增可选参数 `vector_search_repo=None, embedding_service=None`；`execute()` 方法在 `article_repo.save()` 返回 saved 后，检查 embedding_service.is_ready()，若就绪则生成 `f"{title}\n{summary}"` 的 embedding，构建 metadata（user_id, title, stock_codes 逗号分隔, industries 逗号分隔, event_type），调用 `vector_search_repo.add("knowledge_articles", f"article_{id}", ...)` 写入 ChromaDB。整个 embedding 步骤包裹在 try-except 中，失败仅 logger.warning，不阻塞返回 saved。参照 research.md R9.1
- [x] T015 [US1] 改造 `backend/app/application/use_cases/manage_article.py` 的 `DeleteArticleUseCase`：构造函数新增可选参数 `vector_search_repo=None`；`execute()` 方法在 MySQL 软删除后，调用 `vector_search_repo.delete("knowledge_articles", f"article_{article_id}")`，try-except 包裹。参照 research.md R9.4
- [x] T016 [US1] 改造 `backend/app/routers/analysis.py` 的文章保存路由：从 `request.app.state` 获取 `embedding_service` 和 `vector_search_repo`，传入 `SaveArticleUseCase(article_repo, industry_repo, vector_repo, embedding_svc)`。删除路由同理注入 vector_search_repo 到 DeleteArticleUseCase。参照 research.md R9.6
- [x] T017 [US1] 改造 `backend/app/infrastructure/workflow/nodes/retrieve.py` 的 `create_retrieve_node`：函数签名新增 `vector_search_repo=None, embedding_service=None` 参数。内部逻辑：若两者可用且 embedding_service.is_ready()，先 embed(query_text[:80])，再 vector_search_repo.search(embedding, top_k=3, filters={user_id}, threshold=0.7)；若返回空列表或异常，回退到现有 MySQLSearchRepository FULLTEXT 搜索。输出格式 `{"search_results": [...]}` 保持与现有一致。参照 research.md R3 和 data-model.md Data Flow 3
- [x] T018 [US1] 改造 `backend/app/infrastructure/workflow/graph/analysis_graph.py` 的 `build_analysis_graph`：函数签名新增 `vector_search_repo=None, embedding_service=None` 参数，传递给 `create_retrieve_node(session_factory, vector_search_repo, embedding_service)`
- [x] T019 [US1] 单元测试 retrieve 节点向量检索 `backend/tests/unit/infrastructure/test_retrieve_node_vector.py`：测试向量检索有结果时返回向量结果、向量检索无结果时回退 FULLTEXT、embedding_service 不可用时直接走 FULLTEXT、输出格式与现有兼容

**Checkpoint**: US1 完成 — retrieve 节点使用语义检索，文章保存自动生成 embedding，降级机制正常工作

---

## Phase 4: User Story 2 - 事件雷达知识库精准联动 (Priority: P2)

**Goal**: 事件入库时自动生成 embedding 写入 ChromaDB；事件-文章关联从行业+股票交集匹配升级为语义相似度匹配，返回 top 3 相关文章及相关度百分比。

**Independent Test**: 创建一条影响事件（如涉及新能源政策），验证"知识库关联"区域返回语义相关的历史分析文章（含相似度百分比），且无语义结果时回退到行业+股票交集匹配。

### Implementation for User Story 2

- [x] T020 [US2] 改造 `backend/app/application/use_cases/event_radar.py` 的 `EventRadarUseCase`：构造函数新增 `vector_search_repo=None, embedding_service=None` 参数。`crawl_and_process()` 方法在 `event_repo.create(event)` 之后、`article_repo.create(impact_article)` 之前，检查 embedding_service 可用性，生成 `f"{event.title}\n{event.summary or ''}"` 的 embedding，构建 metadata（title, affected_stocks 逗号分隔, affected_industries 逗号分隔, sentiment），调用 `vector_search_repo.add("impact_events", f"event_{id}", ...)` 写入。try-except 包裹，失败不阻塞采集。参照 research.md R9.2
- [x] T021 [US2] 改造 `backend/app/application/use_cases/event_radar.py` 的 `_find_related_analyses()` 方法：当 embedding_service 可用时，先生成事件的 embedding，调用 `vector_search_repo.search(embedding, top_k=3, collection="knowledge_articles", threshold=0.7)`；若返回结果，格式化为 `[{article_id, title, summary, similarity_score}, ...]`（score 转换为百分比）；若向量检索无结果，回退到现有行业+股票交集匹配逻辑。参照 data-model.md Data Flow 4
- [x] T022 [US2] 改造 `backend/app/infrastructure/scheduler/event_crawler_scheduler.py` 的 `setup_scheduler`：函数签名新增 `vector_search_repo=None, embedding_service=None` 参数，传递给 `EventRadarUseCase` 的构造。确保定时采集任务能访问向量服务
- [x] T023 [US2] 单元测试事件语义关联 `backend/tests/unit/application/test_event_semantic_matching.py`：测试事件 embedding 写入 ChromaDB、语义匹配返回相关文章含百分比、无语义结果时回退行业+股票交集、embedding 不可用时走原有逻辑

**Checkpoint**: US2 完成 — 事件入库自动生成 embedding，事件-文章关联支持语义匹配和百分比展示

---

## Phase 5: User Story 3 - 事件去重引擎增强 (Priority: P3)

**Goal**: 在现有 URL hash + Jaccard 去重基础上，新增语义 embedding 相似度作为第三层去重，识别"不同措辞描述同一事件"。

**Independent Test**: 向去重引擎注入两条同事件不同措辞的新闻（"央行降息 25 个基点" vs "人民银行下调基准利率 0.25%"），验证 embedding 相似度 ≥ 0.85 时判定为重复。

### Implementation for User Story 3

- [x] T024 [US3] 改造 `backend/app/domain/services/event_dedup.py`：新增函数 `is_semantic_duplicate(new_title, embedding_service, vector_search_repo, threshold=0.85)`，生成 new_title 的 embedding，在 impact_events 集合中搜索 top-1 相似向量，score >= threshold 返回 True。修改 `assess_event()` 函数签名新增 `embedding_service=None, vector_search_repo=None` 参数，在 URL hash + Jaccard 都未判定重复后，调用 `is_semantic_duplicate()` 作为第三层。前两层已判定重复时跳过语义计算。参照 research.md R5 和 data-model.md Data Flow 5
- [x] T025 [US3] 改造 `backend/app/domain/services/impact_assessment.py` 的 `assess_event()` 调用链：将 `embedding_service` 和 `vector_search_repo` 透传给 `event_dedup` 的语义去重函数。同时在 `EventRadarUseCase.crawl_and_process()` 中将向量服务传入 `assess_event()` 调用
- [x] T026 [US3] 单元测试语义去重 `backend/tests/unit/test_event_dedup_semantic.py`：测试同义标题 embedding 相似度 ≥ 0.85 判定重复、不同事件相似度 < 0.85 不合并、URL hash 优先于语义去重、Jaccard 命中后跳过语义计算、embedding 不可用时跳过语义层

**Checkpoint**: US3 完成 — 事件去重引擎三层过滤（URL hash → Jaccard → 语义 embedding）正常工作

---

## Phase 6: User Story 4 - Agent 上下文注入增强 (Priority: P4)

**Goal**: 个股分析的新闻分析师 Agent 额外获取知识库中语义相关的历史分析摘要（top 3，≤ 2000 字），提升分析深度。

**Independent Test**: 触发一次宁德时代个股深度分析，验证新闻分析师 Agent 的输入中包含知识库历史分析摘要。知识库无相关文章时 Agent 行为不变。

### Implementation for User Story 4

- [x] T027 [US4] 改造 `backend/app/infrastructure/workflow/nodes/stock_news_analyst.py`：函数签名新增 `vector_search_repo=None, embedding_service=None` 参数。当两者可用时，在 Agent 执行前，用股票名称+事件关键词生成 embedding，调用 `vector_search_repo.search(embedding, top_k=3, collection="knowledge_articles", threshold=0.7)` 获取相关历史分析；将结果摘要拼接为上下文字符串（截断至 2000 字），注入到 Agent 的 system prompt 或额外上下文参数中。无结果时不注入，Agent 行为不变。参照 spec.md FR-007
- [x] T028 [US4] 改造 `backend/app/infrastructure/workflow/graph/stock_analysis_graph.py` 的 `build_stock_analysis_graph`：函数签名新增 `vector_search_repo=None, embedding_service=None` 参数，传递给 stock_news_analyst 节点。同时改造 `main.py` 中 `build_stock_analysis_graph()` 调用点，传入向量服务
- [x] T029 [US4] 单元测试 Agent 上下文注入 `backend/tests/unit/test_stock_analyst_context.py`：测试知识库有相关文章时注入上下文、无相关文章时不注入、上下文超过 2000 字时截断、embedding 不可用时 Agent 行为不变

**Checkpoint**: US4 完成 — 新闻分析师 Agent 能获取历史分析上下文，无结果时行为不变

---

## Phase 7: Polish & Cross-Cutting Concerns (运维与收尾)

**Purpose**: 运维工具、端到端验证、文档更新

- [x] T030 [P] 创建向量重建脚本 `backend/scripts/rebuild_vector_index.py`：从 MySQL 全量查询 t_analysis_article（status='completed', deleted='0'）和 t_impact_event，使用 embed_batch() 批量生成 embedding（每批 32 条），写入对应 ChromaDB 集合。支持 `--collection` 参数指定重建单个集合，`--dry-run` 模式仅统计不写入。参照 research.md R9.7
- [x] T031 端到端集成测试 `backend/tests/integration/test_rag_pipeline.py`：模拟完整 RAG 流程——创建文章 → 验证 embedding 写入 → 触发 retrieve 检索 → 验证语义相关性；创建事件 → 验证 embedding 写入 → 事件-文章语义关联 → 验证返回百分比；关闭 RAG 后验证降级到 FULLTEXT

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: 无依赖，立即开始
- **Foundational (Phase 2)**: 依赖 Phase 1 完成 — **阻塞所有 User Story**
- **US1 (Phase 3)**: 依赖 Phase 2 完成 — MVP 核心
- **US2 (Phase 4)**: 依赖 Phase 2 完成，依赖 US1 中的 SaveArticleUseCase 改造（需要文章有 embedding 才能关联）
- **US3 (Phase 5)**: 依赖 Phase 2 完成，依赖 US2 中的事件 embedding 写入（需要 impact_events 集合有数据才能去重）
- **US4 (Phase 6)**: 依赖 Phase 2 完成，依赖 US1 中的 SaveArticleUseCase 改造（需要文章有 embedding）
- **Polish (Phase 7)**: 依赖所有 User Story 完成

### User Story Dependencies

```
Phase 1 (Setup)
    └── Phase 2 (Foundational)
            ├── Phase 3 (US1: retrieve + 文章embedding)  ← MVP
            │       └── Phase 4 (US2: 事件embedding + 语义关联)
            │               └── Phase 5 (US3: 语义去重)
            └── Phase 6 (US4: Agent上下文注入)
Phase 7 (Polish)
```

### Within Each User Story

- Domain 实体/接口 → Infrastructure 实现 → Application 用例改造 → Workflow 节点改造
- 核心实现 → 单元测试
- 每个 Checkpoint 可独立验证

### Parallel Opportunities

- Phase 1: T001 和 T002 可并行（不同文件）
- Phase 2: T003/T004/T005/T006 可并行（不同文件，纯新增）；T010/T011/T012 可并行（不同测试文件）
- Phase 4 的 T020 和 T021 可并行写入和读取改造（同一文件但不同方法，需注意合并）

---

## Parallel Example: Phase 2 Foundational

```bash
# 第一波：所有纯新增文件可并行
Task: "创建向量检索领域实体 domain/entities/vector_search.py"
Task: "创建向量检索仓储抽象接口 domain/repositories/vector_search_repo.py"
Task: "创建 Embedding 服务抽象接口 domain/services/embedding_service.py"
Task: "创建向量基础设施目录 infrastructure/vector/__init__.py"

# 第二波：实现类（依赖第一波的接口定义）
Task: "实现 Embedding 客户端 infrastructure/vector/embedding_client.py"
Task: "实现 ChromaDB 存储封装 infrastructure/vector/chroma_store.py"

# 第三波：仓储实现 + 初始化注入
Task: "实现向量检索仓储 infrastructure/repositories/chroma_vector_search_repo.py"
Task: "改造 main.py lifespan 初始化 RAG 服务"

# 第四波：单元测试全部可并行
Task: "单元测试 Embedding 客户端 tests/unit/test_embedding_client.py"
Task: "单元测试 ChromaDB 存储 tests/unit/test_chroma_store.py"
Task: "单元测试向量检索仓储 tests/unit/test_vector_search_repo.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup（~5 min）
2. Complete Phase 2: Foundational（~1-2 hr，核心基础设施）
3. Complete Phase 3: US1（~1 hr，retrieve 节点 + 文章 embedding）
4. **STOP and VALIDATE**:
   - 启动服务，检查日志出现 "RAG 初始化完成"
   - 保存一篇文章，检查日志出现 "embedding generated"
   - 触发事件分析，检查 retrieve 节点使用向量检索
   - 设置 `RAG_ENABLED=false`，验证降级到 FULLTEXT
5. MVP 可交付

### Incremental Delivery

1. Setup + Foundational → 基础设施就绪
2. US1 → retrieve 语义检索 + 文章 embedding → **MVP!**
3. US2 → 事件 embedding + 知识库精准联动 → 独有壁垒功能
4. US3 → 事件语义去重 → 采集质量提升
5. US4 → Agent 上下文注入 → 个股分析深度提升
6. Polish → 运维脚本 + 端到端测试

### Key Risk Mitigation

- **模型加载失败**：Phase 2 的 T007 已处理降级（is_ready 返回 False）
- **ChromaDB 写入失败**：所有写入操作在 try-except 中，不阻塞主流程
- **性能回归**：T010/T011/T012 单元测试覆盖延迟验证；SC-004/SC-005 可在集成测试中测量

---

## Notes

- [P] tasks = 不同文件，无依赖冲突
- [Story] label 映射到 spec.md 中的 User Story
- 每个 User Story 可独立完成和测试
- 提交粒度：每完成一个 task 或逻辑分组后提交
- 任何 Checkpoint 处都可停下来独立验证
- 避免跨 Story 的硬依赖——US2/US3/US4 在向量无数据时通过回退机制仍可正常工作
