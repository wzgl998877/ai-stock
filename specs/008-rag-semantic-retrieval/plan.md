# Implementation Plan: RAG 语义检索增强

**Branch**: `008-rag-semantic-retrieval` | **Date**: 2026-05-19 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/008-rag-semantic-retrieval/spec.md`

## Summary

为 AI 股票分析平台引入 RAG 语义检索能力，用 ChromaDB + bge-large-zh-v1.5 替代纯 MySQL FULLTEXT 关键词匹配。核心改造 4 个场景：LangGraph retrieve 节点（P1）、事件雷达知识库联动（P2）、事件去重引擎（P3）、Agent 上下文注入（P4）。新增 Domain 层向量检索抽象 + Infrastructure 层 ChromaDB 实现，改造 6 个现有文件，前端零改动。

## Technical Context

**Language/Version**: Python 3.x（后端）+ TypeScript（前端无改动）
**Primary Dependencies**: FastAPI, LangGraph, sentence-transformers, chromadb
**Storage**: MySQL（主库不变）+ ChromaDB（嵌入式向量库，新增）+ Redis（缓存，不变）
**Testing**: pytest（后端单元测试 + 集成测试）
**Target Platform**: Linux/Windows 服务器（Docker 部署）
**Project Type**: Web service（前后端分离）
**Performance Goals**: 语义检索 ≤ 500ms P95，文章保存延迟增加 ≤ 100ms
**Constraints**: CPU 推理，无需 GPU；ChromaDB 嵌入式，无额外服务进程；优雅降级到 FULLTEXT
**Scale/Scope**: 知识库 ≤ 10,000 篇文章，单用户系统

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Notes |
|------|--------|-------|
| 三模块协同优先 | PASS | RAG 增强模块一（retrieve）和模块四（事件雷达）的检索能力，不引入孤岛功能 |
| 个人投研工具边界 | PASS | 纯检索增强，不涉及自动交易或投资建议生成 |
| 简洁实用 (KISS) | PASS | 复用现有 DDD 分层，新增 2 个抽象接口 + 2 个实现类，不过度设计 |
| 技术栈约束 | PASS | Python + FastAPI，ChromaDB 嵌入式不引入额外服务进程 |
| 架构红线 - 不跨层调用 | PASS | 向量检索在 Domain 层定义抽象，Infrastructure 层实现 |
| 架构红线 - 不前端直连 | PASS | 前端零改动，API 契约不变 |
| 数据约束 - Repository 模式 | PASS | 新增 VectorSearchRepository 抽象 + ChromaDB 实现 |
| LLM 统一抽象层 | PASS | Embedding 使用 sentence-transformers，不涉及 LLM SDK 直连 |
| 流式输出成对实现 | PASS | 不涉及新的流式接口 |

**Result**: 全部 GATE 通过，无违规。

## Project Structure

### Documentation (this feature)

```text
specs/008-rag-semantic-retrieval/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
backend/app/
├── domain/
│   ├── repositories/
│   │   ├── vector_search_repo.py          # NEW - 向量检索抽象接口
│   │   └── search_repo.py                 # EXISTING - 不变
│   └── services/
│       ├── embedding_service.py           # NEW - Embedding 服务抽象
│       └── similarity.py                  # EXISTING - 保留（去重仍用 Jaccard）
├── infrastructure/
│   ├── vector/
│   │   ├── __init__.py                    # NEW
│   │   ├── embedding_client.py            # NEW - sentence-transformers 封装
│   │   └── chroma_store.py                # NEW - ChromaDB 存储封装
│   ├── repositories/
│   │   ├── chroma_vector_search_repo.py   # NEW - 向量检索 ChromaDB 实现
│   │   └── mysql_search_repo.py           # EXISTING - 保留（作为兜底）
│   └── workflow/
│       └── nodes/
│           └── retrieve.py                # MODIFY - FULLTEXT → 向量检索
├── application/
│   └── use_cases/
│       ├── manage_article.py              # MODIFY - 保存时生成 embedding
│       ├── event_radar.py                 # MODIFY - 事件-文章语义关联
│       └── search_articles.py             # EXISTING - Phase 3 再改
├── domain/services/
│   ├── event_dedup.py                     # MODIFY - 新增语义去重步骤
│   ├── event_stock_matcher.py             # EXISTING - 不变
│   └── impact_assessment.py               # MODIFY - 知识库匹配改为向量
├── core/
│   └── config.py                          # MODIFY - 新增 RAG 配置项
└── main.py                                # MODIFY - 启动时初始化 embedding 服务

backend/
├── requirements.txt                       # MODIFY - 新增依赖
└── tests/
    └── unit/
        ├── test_embedding_service.py      # NEW
        ├── test_vector_search_repo.py     # NEW
        └── test_retrieve_node.py          # NEW
```

**Structure Decision**: 复用现有后端 DDD 分层结构，新增 `infrastructure/vector/` 目录存放向量相关基础设施，新增 `domain/repositories/vector_search_repo.py` 和 `domain/services/embedding_service.py` 两个抽象。

## Complexity Tracking

> 无宪章违规需要辩护。

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | N/A | N/A |
