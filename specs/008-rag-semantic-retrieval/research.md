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
