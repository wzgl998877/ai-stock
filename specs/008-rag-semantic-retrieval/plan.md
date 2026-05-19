# Implementation Plan: RAG 语义检索增强

**Branch**: `008-rag-semantic-retrieval` | **Date**: 2026-05-19 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/008-rag-semantic-retrieval/spec.md`

## Summary

为 AI 股票分析平台引入 RAG（检索增强生成）功能，使用 `BAAI/bge-large-zh-v1.5` 本地 Embedding 模型 + ChromaDB 嵌入式向量数据库，替代现有的 MySQL FULLTEXT 关键词检索。覆盖 4 个场景：LangGraph retrieve 节点（P1）、事件雷达知识库联动（P2）、事件去重引擎（P3）、Agent 上下文注入（P4）。改造对前端完全透明，API 契约不变。

## Technical Context

**Language/Version**: Python 3.x（与现有后端一致）
**Primary Dependencies**: FastAPI, sentence-transformers >= 2.2.0, chromadb >= 0.4.0, LangGraph
**Storage**: MySQL（主库，不变）+ ChromaDB PersistentClient（新增向量索引）
**Testing**: pytest + pytest-asyncio
**Target Platform**: Linux/Windows 服务器（CPU 推理，无需 GPU）
**Project Type**: Web 服务（FastAPI 后端）
**Performance Goals**: 语义检索响应 ≤ 500ms（≤ 10K 篇文章），Embedding 生成延迟 ≤ 100ms（标题+摘要）
**Constraints**: 模型加载需 ~2GB 内存；向量服务不可用时必须降级到 FULLTEXT
**Scale/Scope**: 知识库数百~数千篇文章，影响事件数万级

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 原则 | 检查结果 | 状态 |
|------|----------|------|
| 三模块协同优先 | RAG 改造仅涉及模块一（AI 分析），不新增跨模块跳转；retrieve 节点和知识库均在模块一内 | PASS |
| 个人投研工具边界 | 无交易能力引入，不涉及自动交易 | PASS |
| 简洁实用 (KISS) | ChromaDB 嵌入式零运维，不引入额外服务；复用现有 DDD 分层 | PASS |
| 后端分层 Router→App→Domain→Infra | VectorSearchRepository 在 Domain 层定义抽象，Infrastructure 层实现 ChromaDB | PASS |
| 前端不直连网络 | 前端零改动，API 契约不变 | PASS |
| 密钥不泄露 | Embedding 模型本地运行，无外部 API Key | PASS |
| 流式输出成对 | 不涉及流式变更（retrieve 节点在 LangGraph 内部） | PASS |
| UI 设计遵循 DESIGN.md | 前端无改动 | PASS |

**Gate Result**: PASS — 无违反

## Project Structure

### Documentation (this feature)

```text
specs/008-rag-semantic-retrieval/
├── plan.md              # This file
├── research.md          # Phase 0 output — 技术决策 + 数据灌入流程
├── data-model.md        # Phase 1 output — ChromaDB Collections + 数据流
├── quickstart.md        # Phase 1 output — 依赖安装 + 启动验证
├── contracts/
│   └── vector-search-interface.md  # Domain 层接口契约
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
backend/app/
├── core/
│   └── config.py                              # [改造] 新增 RAG 配置项
├── domain/
│   ├── entities/
│   │   └── vector_search.py                   # [新增] VectorSearchResult, EmbeddingData
│   ├── repositories/
│   │   └── vector_search_repo.py              # [新增] VectorSearchRepository 抽象接口
│   └── services/
│       ├── embedding_service.py               # [新增] EmbeddingService 抽象接口
│       ├── event_dedup.py                     # [改造] 新增语义 embedding 去重第三层
│       ├── event_stock_matcher.py             # [改造] 事件-文章关联增加语义匹配
│       └── impact_assessment.py               # [改造] 知识库匹配改为向量检索
├── infrastructure/
│   ├── vector/
│   │   ├── __init__.py                        # [新增]
│   │   ├── embedding_client.py                # [新增] sentence-transformers 封装
│   │   └── chroma_store.py                    # [新增] ChromaDB 存储封装
│   ├── repositories/
│   │   └── chroma_vector_search_repo.py       # [新增] VectorSearchRepository 实现
│   ├── workflow/
│   │   ├── graph/
│   │   │   └── analysis_graph.py              # [改造] 注入 vector_search_repo + embedding_service
│   │   └── nodes/
│   │       ├── retrieve.py                    # [改造] FULLTEXT → 向量检索 + 回退
│   │       └── stock_news_analyst.py           # [改造] 注入历史分析上下文 (P4)
│   └── scheduler/
│       └── event_crawler_scheduler.py         # [改造] 注入 embedding 服务
├── application/
│   └── use_cases/
│       ├── manage_article.py                  # [改造] 保存文章时生成 embedding 写入 ChromaDB
│       └── event_radar.py                     # [改造] 事件入库时生成 embedding + 语义关联
├── routers/
│   └── analysis.py                            # [改造] 注入 vector_search_repo + embedding_service
└── main.py                                    # [改造] lifespan 中初始化 Embedding + ChromaDB

tests/
├── unit/
│   ├── test_embedding_client.py               # [新增] Embedding 服务单元测试
│   ├── test_chroma_store.py                   # [新增] ChromaDB 存储单元测试
│   ├── test_vector_search_repo.py             # [新增] 向量检索仓储单元测试
│   ├── test_event_dedup_semantic.py           # [新增] 语义去重单元测试
│   └── test_retrieve_node_vector.py           # [新增] Retrieve 节点向量检索测试
└── integration/
    └── test_rag_pipeline.py                   # [新增] RAG 端到端集成测试
```

**Structure Decision**: 沿用现有后端分层架构（Router → Application → Domain → Infrastructure），向量相关基础设施在 `infrastructure/vector/` 新目录，Domain 层定义抽象接口，完全符合 DDD 分层规范。

## Complexity Tracking

无违反需要记录。
