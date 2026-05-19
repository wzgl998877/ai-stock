# Product Requirements Document: RAG 检索增强生成

**Version**: 1.0
**Date**: 2026-05-19
**Author**: Sarah (Product Owner)
**Quality Score**: 90/100
**核心命题**: 用语义检索替代关键词匹配，让系统"理解"而非"匹配"知识

---

## Executive Summary

当前 AI 股票分析平台的知识库检索完全依赖 MySQL FULLTEXT 关键词匹配。用户搜"新能源补贴影响"无法找到"光伏政策扶持分析"；LangGraph retrieve 节点召回的历史分析上下文质量差，直接影响 AI 分析报告质量；事件雷达的知识库联动仅靠行业+股票交集和 Jaccard 词频重叠，无法实现 PRD 承诺的"你之前分析过的那条政策，和今天这条事件相关度 85%"的精准关联。

本 PRD 定义了 RAG（Retrieval-Augmented Generation）功能的完整需求：引入向量语义检索，覆盖 LangGraph retrieve 节点、事件雷达联动、事件去重、Agent 上下文增强 4 个场景。知识库前端语义搜索（Story 1）延后到 Phase 3，MVP 聚焦于对 AI 分析质量有直接提升的后端场景。技术选型为 ChromaDB（嵌入式向量库）+ bge-large-zh-v1.5（中文语义模型），与现有 DDD 架构无缝集成。

---

## Problem Statement

**Current Situation**: 系统有 3 个独立但共享同一短板的检索子系统——知识库 FULLTEXT 搜索、LangGraph retrieve 节点、事件雷达 Jaccard 相似度。三者都只能做关键词级别的匹配，无法理解语义。

**Proposed Solution**: 引入 embedding 模型 + 向量数据库，在现有 DDD 分层架构的 Domain/Infrastructure 层新增向量检索能力，上层业务透明切换。

**Business Impact**:
- AI 分析报告质量直接提升（retrieve 节点上下文更相关）
- 事件雷达的"独有壁垒"——知识库历史分析精准关联——从承诺变为现实
- 事件去重更精准，减少重复事件噪音

---

## Success Metrics

**Primary KPIs:**

| 指标 | 目标 | 衡量方式 |
|------|------|----------|
| 语义检索召回率 | ≥ 85% | 构造 50 组测试 query + 人工标注相关文章，对比 FULLTEXT 和向量检索的召回率 |
| 语义检索准确率 | ≥ 80% | 同上测试集，top-5 结果中相关文章的占比 |
| retrieve 节点上下文相关性 | ≥ 4.0/5 | 人工评估 20 次事件分析中 retrieve 节点返回的上下文与当前分析的相关性 |
| 向量检索延迟 | ≤ 500ms | P95 延迟，知识库规模 ≤ 10,000 篇文章 |

**Validation**: 上线后 1 周内完成测试集评测，重点关注召回率和 retrieve 节点相关性提升。

---

## User Personas

### Primary: A 股个人投资者（散户）

- **Role**: 持有 ≤ 30 只自选股的个人投资者（复用现有画像）
- **Goals**: AI 分析能引用更相关的历史上下文，事件关联更精准
- **Pain Points**: AI 分析时上下文检索质量差，分析报告与历史分析脱节；事件雷达的知识库联动不够精准
- **Technical Level**: 中等，不感知后端技术变化
- **RAG 对用户的价值**: AI 分析更准 → 事件关联更精准 → 知识库越用越懂你，全程透明无感知

---

## User Stories & Acceptance Criteria

### Story 1：事件分析上下文检索增强

**作为** 正在使用事件分析功能的散户
**我希望** AI 在分析事件时能引用更相关的历史分析作为上下文
**从而** 分析报告更有深度，避免重复分析

**Acceptance Criteria:**
- [ ] LangGraph retrieve 节点完全替换为向量检索
- [ ] retrieve 节点返回 top 3 语义最相关的历史文章（数量不变）
- [ ] 向量检索无结果时回退到原有 FULLTEXT 检索
- [ ] retrieve 节点的输入（query）和输出（context articles）接口不变，下游 summarize_context 节点无需修改
- [ ] 事件分析的完整流程（分类→搜索→加载→检索→总结→分析）不变

---

### Story 2：事件雷达知识库精准联动

**作为** 正在查看影响事件的散户
**我希望** 事件卡片上展示的历史分析关联更精准
**从而** 看到真正相关的历史分析，而非仅靠行业重叠匹配

**Acceptance Criteria:**
- [ ] 影响事件与知识库文章的关联从 Jaccard 词频匹配升级为语义相似度匹配
- [ ] 关联阈值可配置（默认 cosine similarity ≥ 0.7）
- [ ] 事件详情 Drawer 的"知识库关联"区域展示语义最相关的 top 3 历史文章
- [ ] 关联结果包含相似度百分比（如"相关度 85%"）
- [ ] 向量匹配无结果时回退到现有行业+股票交集匹配

---

### Story 3：事件去重引擎增强

**作为** 系统运维者
**我希望** 事件采集管线能更精准地识别同一事件的不同报道
**从而** 减少重复事件，提高影响判断效率

**Acceptance Criteria:**
- [ ] 事件去重引擎在现有 URL hash + TF-IDF 标题相似度基础上，新增标题/摘要的语义 embedding 相似度
- [ ] 语义去重阈值可配置（默认 cosine similarity ≥ 0.85）
- [ ] 语义去重作为现有去重流程的补充，不替代 URL hash 精确去重
- [ ] 去重管线执行顺序不变：URL hash → TF-IDF → 语义相似度

---

### Story 4：Agent 上下文注入增强

**作为** 正在使用个股深度分析的散户
**我希望** AI 分析师在分析时能参考更多相关的历史分析
**从而** 获得更有依据的分析建议

**Acceptance Criteria:**
- [ ] 个股分析工作流中，新闻分析师 Agent 执行时可获取语义相关的历史分析上下文
- [ ] 上下文注入方式：在 Agent 工具调用的基础上，额外注入 top 3 相关历史分析摘要
- [ ] 注入的上下文长度 ≤ 2000 字（避免占用过多 token）
- [ ] 不改变现有 Agent 工具调用链和数据流
- [ ] 如果无相关历史分析，不注入额外上下文，Agent 行为不变

---

## Functional Requirements

### Core Feature 1: Embedding 生成服务

**Description**: 统一的文本 embedding 生成服务，供所有 RAG 场景共用。

**Technical Design:**
- 模型：`bge-large-zh-v1.5`（BAAI 开源中文语义模型，1024 维）
- 推理框架：`sentence-transformers`
- 部署方式：与 FastAPI 同进程，无需额外服务
- 模型缓存：首次下载后本地缓存，模型文件约 1.3GB

**Embedding 生成时机:**
1. 文章保存到知识库时 → 同步生成标题+摘要的 embedding，异步生成正文的 embedding
2. 事件采集入库时 → 生成事件标题+摘要的 embedding
3. 搜索 query → 实时生成 query embedding
4. retrieve 节点 → 实时生成分析 query embedding

**Performance:**
- 单条文本 embedding 生成：< 100ms（GPU）/ < 500ms（CPU）
- 批量 embedding（100 条）：< 5s（CPU）

**Edge Cases:**
- 模型加载失败：启动时预加载，加载失败则回退到 FULLTEXT 模式，不阻塞系统启动
- 文本为空：跳过 embedding 生成，不写入向量库
- 模型文件未下载：首次启动自动下载，提供手动下载脚本作为备选

---

### Core Feature 2: 向量存储与检索

**Description**: 基于 ChromaDB 的向量存储和检索服务。

**Technical Design:**
- 存储引擎：ChromaDB（嵌入式，PersistentClient，数据存储在本地文件）
- 集合设计：
  - `knowledge_articles`：知识库文章（key=article_id, embedding=标题+摘要, metadata=title/stock_codes/industries/event_type）
  - `impact_events`：影响事件（key=event_id, embedding=标题+摘要, metadata=title/affected_stocks/affected_industries）
- 检索方式：cosine similarity，支持 metadata 过滤

**Retrieval Strategy (向量为主 + FULLTEXT 兜底):**
```
用户 Query
  ↓ 生成 query embedding
  ↓ 向量检索（cosine similarity ≥ 阈值）
  ├─ 有结果 → 返回向量检索结果
  └─ 无结果 → 回退到 FULLTEXT 检索
       ├─ 有结果 → 返回 FULLTEXT 结果
       └─ 无结果 → 返回空列表
```

**Edge Cases:**
- ChromaDB 文件损坏：重建索引（从 MySQL 全量重新生成 embedding）
- 检索结果与 FULLTEXT 结果差异大：以向量检索为主，FULLTEXT 仅兜底
- 集合为空（首次部署）：向量检索返回空，回退到 FULLTEXT

---

### Core Feature 3: 混合检索策略

**Description**: 向量检索为主、FULLTEXT 为兜底的检索策略，确保在任何情况下都有结果。

**Applicable Scenarios:**

| 场景 | 主检索 | 兜底 | 特殊处理 |
|------|--------|------|----------|
| retrieve 节点 | 向量检索 top 3 | FULLTEXT top 3 | 无 |
| 事件-文章关联 | 向量相似度 ≥ 0.7 | 行业+股票交集 | 无 |
| 事件去重 | 语义相似度 ≥ 0.85 | TF-IDF ≥ 0.7 | URL hash 精确去重优先 |
| Agent 上下文 | 向量检索 top 3 | 无兜底 | 无结果时不注入 |
| 知识库前端搜索（Phase 3） | 向量检索 top 10 | FULLTEXT top 10 | 延后实现 |

---

### Core Feature 4: 文章保存时 Embedding 集成

**Description**: 知识库文章保存时自动生成并存储 embedding。

**Processing Flow:**
```
文章保存
  ↓ 保存到 MySQL（现有逻辑不变）
  ↓ 同步生成标题+摘要的 embedding（< 100ms）
  ↓ 写入 ChromaDB（knowledge_articles 集合）
  ↓ 异步生成正文 embedding（可选，用于更精准的检索）
  ↓ 更新 ChromaDB（覆盖 embedding 为更精准的版本）
```

**Edge Cases:**
- embedding 生成失败：文章正常保存到 MySQL，日志记录 embedding 失败，不影响保存流程
- ChromaDB 写入失败：同上，MySQL 优先，向量库失败不影响主流程
- 文章更新（重新保存）：覆盖 ChromaDB 中对应的 embedding

---

### Out of Scope (本期不做)

| 功能 | 说明 |
|------|------|
| 知识库前端语义搜索 | 延后到 Phase 3，MVP 聚焦后端 retrieve 节点和事件雷达联动 |
| 历史文章全量 embedding 迁移 | MVP 只对新文章生成 embedding，历史文章后续迁移 |
| Embedding 模型微调 | 使用预训练模型，不基于金融数据微调 |
| Reranker 重排序 | 粗排后精排，Phase 2 考虑 |
| 向量数据库迁移到 Qdrant | ChromaDB 满足当前数据量，未来按需迁移 |
| 前端 UI 变化 | 完全透明切换，前端无感知 |
| GPU 推理加速 | CPU 推理满足 ≤500ms 延迟要求，暂不需要 GPU |
| 多模态 embedding | 仅文本 embedding，不支持图表/图片 |

---

## Technical Constraints

### Performance

| 指标 | 目标 | 说明 |
|------|------|------|
| 向量检索延迟 | ≤ 500ms (P95) | 知识库 ≤ 10,000 篇文章 |
| 单条 embedding 生成 | ≤ 500ms | CPU 推理 |
| 文章保存延迟增加 | ≤ 100ms | 仅同步生成标题+摘要的 embedding |
| ChromaDB 存储空间 | ≤ 500MB | 10,000 篇文章 × 1024 维 × 4 bytes |
| 模型加载时间 | ≤ 30s | 启动时预加载，bge-large-zh-v1.5 |

### Architecture Constraints

- **DDD 分层**：向量检索能力在 Domain 层定义抽象接口，Infrastructure 层实现 ChromaDB 适配
- **不破坏现有接口**：所有 API 契约不变，前端零改动
- **优雅降级**：ChromaDB 不可用时自动回退到 FULLTEXT，不阻塞任何业务流程
- **依赖最小化**：新增依赖仅 sentence-transformers + chromadb，不引入额外服务

### Security & Compliance

- 向量数据与业务数据共享同一用户隔离模型（`user_id` 在 metadata 中）
- embedding 模型本地运行，不向外部 API 发送用户数据
- ChromaDB 数据文件存储在服务器本地，与 MySQL 同级安全

---

## Architecture Design

### 新增文件结构

```
backend/app/
  domain/
    repositories/
      vector_search_repo.py          # 向量检索抽象接口（新增）
    services/
      embedding_service.py           # Embedding 服务抽象（新增）
  infrastructure/
    vector/
      __init__.py
      embedding_client.py            # sentence-transformers 封装（新增）
      chroma_store.py                # ChromaDB 存储封装（新增）
    repositories/
      chroma_vector_search_repo.py   # 向量检索实现（新增）
```

### 核心接口设计

```python
# domain/repositories/vector_search_repo.py
class VectorSearchRepository(ABC):
    @abstractmethod
    async def search(self, query_embedding: list[float],
                     top_k: int = 5,
                     filters: dict | None = None,
                     threshold: float = 0.7) -> list[SearchResult]: ...

    @abstractmethod
    async def add(self, doc_id: str, embedding: list[float],
                  metadata: dict, document: str): ...

    @abstractmethod
    async def delete(self, doc_id: str): ...

    @abstractmethod
    async def update(self, doc_id: str, embedding: list[float] | None = None,
                     metadata: dict | None = None): ...


# domain/services/embedding_service.py
class EmbeddingService(ABC):
    @abstractmethod
    async def embed(self, text: str) -> list[float]: ...

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]: ...
```

### 改造文件清单

| 文件 | 改造内容 |
|------|----------|
| `infrastructure/workflow/nodes/retrieve.py` | FULLTEXT → 向量检索，无结果时回退 FULLTEXT |
| `application/use_cases/manage_article.py` | 文章保存时调用 EmbeddingService + VectorSearchRepo |
| `domain/services/event_dedup.py` | 新增语义相似度去重步骤 |
| `domain/services/event_stock_matcher.py` | 事件-文章关联改为语义匹配 |
| `domain/services/impact_assessment.py` | 影响判断中的知识库匹配改为向量检索 |
| `core/config.py` | 新增 RAG 相关配置项 |
| `requirements.txt` | 新增 sentence-transformers、chromadb |

### 新增配置项

```python
# core/config.py 新增
RAG_ENABLED: bool = True                    # RAG 总开关
RAG_EMBEDDING_MODEL: str = "BAAI/bge-large-zh-v1.5"
RAG_VECTOR_DB_PATH: str = "./data/vector_db"  # ChromaDB 数据目录
RAG_SIMILARITY_THRESHOLD: float = 0.7        # 语义相似度阈值
RAG_DEDUP_THRESHOLD: float = 0.85            # 去重语义相似度阈值
RAG_MAX_CONTEXT_LENGTH: int = 2000           # Agent 上下文注入最大字符数
```

---

## MVP Scope & Phasing

### Phase 0: 基础设施（3-5 天）

- [ ] 安装 sentence-transformers + chromadb 依赖
- [ ] 实现 EmbeddingService（Domain 层抽象 + Infrastructure 层 sentence-transformers 实现）
- [ ] 实现 VectorSearchRepository（Domain 层抽象 + Infrastructure 层 ChromaDB 实现）
- [ ] 配置项注入（config.py + .env）
- [ ] 启动时模型预加载 + ChromaDB 初始化
- [ ] 模型下载脚本（手动备选）

### Phase 1: 核心检索改造（1 周）

- [ ] **Story 1**：retrieve 节点完全替换（retrieve.py 改造 + 无结果回退 FULLTEXT）
- [ ] **Story 3 补充**：文章保存时 embedding 集成（manage_article.py 改造）
- [ ] 测试集构建（50 组 query + 人工标注）并评测召回率/准确率

### Phase 2: 事件雷达增强（1 周）

- [ ] **Story 2**：事件-文章语义关联（event_stock_matcher.py / impact_assessment.py）
- [ ] **Story 3**：事件去重引擎加入语义相似度（event_dedup.py）
- [ ] 影响事件入库时 embedding 生成集成

### Phase 3: 知识库搜索 + Agent 增强（持续）

- [ ] 知识库前端语义搜索（search_articles.py 改造 + 向量为主 FULLTEXT 兜底）
- [ ] **Story 4**：Agent 上下文注入增强
- [ ] 检索结果质量监控（日志埋点，统计向量 vs FULLTEXT 命中率）
- [ ] 历史文章全量 embedding 迁移脚本
- [ ] Reranker 重排序（可选）

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation Strategy |
|------|------------|--------|---------------------|
| bge 模型对金融术语理解不足 | Medium | Medium | 构建金融领域测试集验证；后续可用金融微调模型替代 |
| 向量检索返回语义相关但事实无关的文章 | Medium | High | 混合策略：向量检索 + metadata 过滤（行业/股票）+ FULLTEXT 兜底 |
| ChromaDB 文件损坏导致向量数据丢失 | Low | Medium | 向量数据可从 MySQL 全量重建；不影响主数据 |
| 模型加载增加启动时间（~30s） | Low | Low | 启动时后台加载，加载完成前回退到 FULLTEXT 模式 |
| 新增依赖导致部署包体积增大（模型 1.3GB） | Low | Low | 模型文件独立管理，可选预下载或 Docker 镜像内置 |
| CPU 推理延迟超出 500ms 目标 | Low | Medium | 批量推理优化；必要时引入 ONNX Runtime 加速 |

---

## Dependencies & Blockers

**Dependencies:**
- sentence-transformers 和 chromadb 的 Python 版本兼容性（当前 Python 3.x，预计无问题）
- bge-large-zh-v1.5 模型的首次下载（需网络环境或手动下载）
- 磁盘空间 ≥ 2GB（模型 1.3GB + ChromaDB 数据）

**Known Blockers:**
- 无已知阻塞项

---

## Appendix

### Glossary

- **RAG (Retrieval-Augmented Generation)**: 检索增强生成，先从知识库检索相关内容，再将检索结果作为上下文提供给 LLM
- **Embedding**: 将文本转换为固定维度的数值向量，语义相近的文本向量距离更近
- **ChromaDB**: 开源嵌入式向量数据库，Python 原生，无需独立服务
- **bge-large-zh-v1.5**: BAAI 发布的中文语义向量模型，1024 维，适合中文语义检索
- **Cosine Similarity**: 余弦相似度，衡量两个向量方向的相似程度，范围 [-1, 1]
- **FULLTEXT**: MySQL 全文索引，基于关键词的文本检索
- **混合检索**: 向量语义检索 + 关键词检索的组合策略

### References

- 产品概览 v2：`docs/v2/product-overview-v2.md`
- AI 分析 PRD v2：`docs/v2/ai-analysis-prd-v2.md`
- 事件雷达 PRD：`docs/v2/event-radar-prd.md`
- 行情数据 PRD v2：`docs/v2/market-data-prd-v2.md`
- 后端架构规范：`rules/backend.md`
- bge 模型：https://huggingface.co/BAAI/bge-large-zh-v1.5
- ChromaDB：https://www.trychroma.com/

---

*This PRD was created through interactive requirements gathering with quality scoring to ensure comprehensive coverage of business, functional, UX, and technical dimensions.*
