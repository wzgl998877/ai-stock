# Implementation Plan: 个股多Agent深度分析

**Branch**: `003-stock-analysis` | **Date**: 2026-04-22 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-stock-analysis/spec.md`

## Summary

将 TradingAgents-CN 的多Agent协作分析能力集成到现有 ai-stock 项目，实现个股深度分析功能。用户输入A股股票代码，系统通过4位专业化分析师（技术面/基本面/新闻/情绪）→ 看多看空辩论 → 风险辩论 → 结构化决策的完整流程，实时流式展示分析过程与结论。技术方案：复用现有 AIService 和 LangGraph 工作流引擎，构建独立的 StockAnalysisGraph，通过扩展 SSE 事件体系支持 Agent 级别的实时输出。

## Technical Context

**Language/Version**: Python 3.10+（后端）、TypeScript（前端）
**Primary Dependencies**: FastAPI, LangGraph, langchain-core, AKShare, React 18, Ant Design 5
**Storage**: MySQL（主库，扩展 AnalysisArticle/ChatSession/ChatMessage）+ Redis（股票数据缓存）
**Testing**: pytest（后端）、Vitest（前端）
**Target Platform**: Web 应用（PC端为主）
**Project Type**: Web 应用（前后端分离）
**Performance Goals**: 完整分析≤5分钟，快速分析≤1分钟，首Agent输出≤5秒
**Constraints**: 遵循 DDD 分层（Router→Application→Domain→Infrastructure），Workflow 不直接访问DB/AI，Prompt 模板化管理
**Scale/Scope**: 单用户，A股约5000只股票

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### 原则 I：三模块协同优先

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 标明归属模块 | ✅ PASS | 归属模块一（AI 分析 & 知识库），增强功能 |
| 与其它模块联动 | ✅ PASS | 分析结果关联股票代码 → 知识库股票视图 → 模块二K线跳转（预留） |
| 不做排除的能力 | ✅ PASS | 不做自动交易、Level 2、多市场（A股 only） |

### 原则 II：个人投研工具边界

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 不实现自动下单 | ✅ PASS | 仅输出分析建议 |
| 体现数据源延迟 | ✅ PASS | AKShare 数据15-30分钟延迟，分析结果中标注 |
| 保留免责声明 | ✅ PASS | FR-010 要求所有结果含"不构成投资建议" |

### 原则 III：简洁实用

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 最小变更 | ✅ PASS | 扩展现有模型和 AIService，不重构现有代码 |
| 复用现有抽象 | ✅ PASS | 复用 AIService、ChatUseCase、AnalysisArticle、知识库 |
| 不提前设计 | ✅ PASS | 向量记忆/反思暂不实现，港股/美股暂不支持 |

### 技术约束

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 后端分层 | ✅ PASS | 新代码遵守 Router→Application→Domain→Infrastructure |
| 前端 Service 层 | ✅ PASS | 新 API 调用集中在 services/ |
| 统一 AI 调用层 | ✅ PASS | Agent 通过 AIService 调用 LLM，不直接使用 langchain SDK |
| 流式输出成对 | ✅ PASS | 后端 SSE + 前端 EventSource 流式接收 |
| Prompt 模板化 | ✅ PASS | 所有 Prompt 在 prompts/ 目录，Node 内不拼接 |
| 数据库经 Repository | ✅ PASS | 新增字段通过 Repository 访问 |
| 金额用 Decimal | ✅ PASS | 目标价、置信度等数值字段使用 Decimal |

### Post-Design Re-check

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 新增 AIService 方法不破坏现有接口 | ✅ PASS | 新增可选参数，向后兼容 |
| StockAnalysisGraph 不影响现有 AnalysisGraph | ✅ PASS | 独立 Graph，通过 Application 层选择 |
| 数据模型扩展向后兼容 | ✅ PASS | 新增字段有默认值，现有数据不受影响 |
| SSE 新事件类型向后兼容 | ✅ PASS | 新增事件类型，前端忽略未知类型 |

## Project Structure

### Documentation (this feature)

```text
specs/003-stock-analysis/
├── plan.md              # 本文件
├── research.md          # Phase 0 研究输出
├── data-model.md        # Phase 1 数据模型
├── quickstart.md        # Phase 1 快速启动
├── contracts/
│   └── api-contracts.md # Phase 1 API 契约
└── tasks.md             # Phase 2 任务（/speckit.tasks 生成）
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── routers/
│   │   └── chat.py                          # 扩展：个股分析 SSE 流端点
│   ├── application/
│   │   ├── dtos/
│   │   │   └── stock_analysis_dto.py        # 新增：个股分析 DTO
│   │   └── use_cases/
│   │       ├── chat_use_case.py             # 扩展：支持 stock_analysis 事件类型
│   │       └── stock_analysis_use_case.py   # 新增：个股分析用例（SSE编排）
│   ├── domain/
│   │   ├── entities/
│   │   │   └── chat_session.py              # 扩展：session_type, config 字段
│   │   ├── services/
│   │   │   ├── analysis_parser.py           # 扩展：支持多Agent输出解析
│   │   │   └── signal_extractor.py          # 新增：结构化决策提取（适配自 TradingAgents-CN）
│   │   └── value_objects/
│   │       └── agent_type.py                # 新增：Agent标识枚举
│   ├── infrastructure/
│   │   ├── ai/
│   │   │   └── ai_service.py                # 扩展：model/temperature参数、tool_call增强
│   │   ├── db/
│   │   │   ├── models.py                    # 扩展：article_type, analysis_data, session_type, config, agent_data
│   │   │   └── migrations/                  # 新增迁移
│   │   ├── repositories/
│   │   │   └── mysql_chat_repo.py           # 扩展：支持新字段
│   │   └── workflow/
│   │       ├── graph/
│   │       │   └── stock_analysis_graph.py   # 新增：多Agent分析图
│   │       ├── nodes/
│   │       │   ├── stock_market_analyst.py   # 新增：技术面分析节点
│   │       │   ├── stock_fundamentals_analyst.py # 新增：基本面分析节点
│   │       │   ├── stock_news_analyst.py     # 新增：新闻分析节点
│   │       │   ├── stock_sentiment_analyst.py # 新增：情绪分析节点
│   │       │   ├── bull_researcher.py        # 新增：看多研究员节点
│   │       │   ├── bear_researcher.py        # 新增：看空研究员节点
│   │       │   ├── research_manager.py       # 新增：研究管理器节点
│   │       │   ├── trader.py                 # 新增：交易员节点
│   │       │   ├── risky_debator.py          # 新增：激进风险节点
│   │       │   ├── safe_debator.py           # 新增：保守风险节点
│   │       │   ├── neutral_debator.py        # 新增：中立风险节点
│   │       │   ├── risk_judge.py             # 新增：风险裁决节点
│   │       │   ├── signal_extractor.py       # 新增：信号提取节点
│   │       │   └── msg_clear.py             # 新增：消息清除节点
│   │       ├── state/
│   │       │   └── stock_analysis_state.py   # 新增：三层State定义
│   │       ├── prompts/
│   │       │   └── stock_analysis/           # 新增：13个Agent的Prompt模板
│   │       └── tools/
│   │           └── stock_data_toolkit.py     # 新增：金融数据工具集
│   └── core/
│       └── config.py                         # 扩展：分析配置参数
└── tests/

frontend/
├── src/
│   ├── pages/
│   │   └── StockAnalysisPage.tsx             # 新增：个股分析主页面
│   ├── components/
│   │   ├── stock-analysis/
│   │   │   ├── StockSearchInput.tsx          # 新增：股票搜索输入
│   │   │   ├── AnalysisModeSelector.tsx      # 新增：分析模式选择器
│   │   │   ├── AgentProgressPanel.tsx        # 新增：Agent进度面板
│   │   │   ├── AgentReportCard.tsx           # 新增：Agent报告卡片
│   │   │   ├── DebateTimeline.tsx            # 新增：辩论时间线
│   │   │   └── DecisionCard.tsx              # 新增：决策卡片
│   │   └── layout/
│   │       └── AppLayout.tsx                 # 扩展：侧边栏新增入口
│   ├── services/
│   │   └── stockAnalysisService.ts           # 新增：个股分析 API
│   ├── store/
│   │   └── stockAnalysisStore.ts             # 新增：分析状态管理
│   ├── domain/
│   │   ├── types.ts                          # 扩展：Agent类型、分析事件类型
│   │   └── constants.ts                      # 扩展：Agent显示名称、分析模式
│   └── App.tsx                               # 扩展：新增路由
└── tests/
```

**Structure Decision**: 采用现有的前后端分离架构，后端在 `backend/app/` 下按 DDD 分层扩展，前端在 `frontend/src/` 下按现有分层模式扩展。新增文件集中在 `stock-analysis` 相关目录，对现有代码仅做最小扩展。

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| AIService 新增 model 参数 | 不同 Agent 需要不同模型（深度思考 vs 快速思考） | 全部使用同一模型会导致 Research Manager/Risk Judge 推理质量不足 |
| 扩展 SSE 事件类型 | 多Agent需区分不同Agent输出和辩论过程 | 复用现有 content 事件无法区分Agent来源，前端无法正确展示 |
| 新增 stock_analysis_graph.py | 多Agent分析图与预处理图结构完全不同 | 混入现有图会导致职责混乱，违反单一职责原则 |
