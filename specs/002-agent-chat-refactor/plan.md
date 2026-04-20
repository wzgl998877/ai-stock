# Implementation Plan: Agent 对话式投研助手

**Branch**: `002-agent-chat-refactor` | **Date**: 2026-04-20 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-agent-chat-refactor/spec.md`

## Summary

将 AI 分析模块从"单次表单分析"升级为"ChatGPT 式对话投研助手"。核心变更：
1. **前端**：侧边栏（会话列表）+ 主区域消息堆叠 + 保留四个事件类型按钮
2. **后端**：ChatSession/ChatMessage 持久化 + 多轮对话 + LangGraph Agent 自主搜索
3. **SSE**：新增 `thinking` 事件类型展示思维链

## Technical Context

**Language/Version**: Python 3.13 + TypeScript
**Primary Dependencies**: FastAPI, React 18, Ant Design 5, LangGraph, Zustand
**Storage**: MySQL（会话/消息持久化）
**Testing**: pytest, Vitest
**Target Platform**: Web（桌面端）
**Project Type**: Web application (frontend + backend)
**Performance Goals**: 首 token ≤ 3s，思维链首步 ≤ 1s
**Constraints**: SSE 格式向后兼容，不引入完整 langchain 包
**Scale/Scope**: 个人投研工具，单用户

## Constitution Check

| Gate | Status | Notes |
|------|--------|-------|
| 三模块协同 | ✅ PASS | 改动仅限模块一（AI 分析） |
| 个人投研工具边界 | ✅ PASS | 无自动交易，保留"不构成投资建议" |
| 简洁实用 | ✅ PASS | 复用现有 ChatSession/ChatMessage 实体和 ORM |
| 技术栈约束 | ✅ PASS | React+AntDesign+Zustand / Python+FastAPI 不变 |
| 架构红线 | ✅ PASS | Chat 路由遵循四层架构，LangGraph 在 Infrastructure 层 |
| LLM 统一抽象层 | ✅ PASS | Agent 节点通过 AIService 调用 LLM |
| SSE 流式输出 | ✅ PASS | 扩展 SSE 协议（新增 thinking 类型），现有格式不变 |
| 前端 Service 层 | ✅ PASS | 新增 chatService |

## Project Structure

### Documentation (this feature)

```text
specs/002-agent-chat-refactor/
├── plan.md
├── spec.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── api-contracts.md
└── checklists/
    └── requirements.md
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── routers/
│   │   ├── analysis.py              # 保留（保存/相似检测）
│   │   └── chat.py                  # 新增（会话 CRUD + 流式对话）
│   ├── application/
│   │   ├── dtos/
│   │   │   └── chat_dto.py          # 新增
│   │   └── use_cases/
│   │       └── chat_use_case.py     # 新增
│   ├── domain/
│   │   ├── entities/
│   │   │   ├── chat_session.py      # 修改（+event_type）
│   │   │   └── chat_message.py      # 修改（+thinking_steps, event_type）
│   │   └── repositories/
│   │       └── chat_repo.py         # 已有（接口完整）
│   ├── infrastructure/
│   │   ├── ai/
│   │   │   └── ai_service.py        # 修改（支持 messages 数组）
│   │   ├── db/
│   │   │   └── models.py            # 修改（ChatMessage 增加字段）
│   │   ├── repositories/
│   │   │   └── mysql_chat_repo.py   # 新增
│   │   └── workflow/
│   │       ├── nodes/
│   │       │   ├── agent_classify.py # 新增（LLM tool calling）
│   │       │   └── ...
│   │       ├── tools/
│   │       │   └── web_search.py    # 新增（Tavily）
│   │       └── graph/
│   │           └── analysis_graph.py # 修改（条件边 + thinking）
│   └── main.py                      # 修改
└── requirements.txt                  # 修改

frontend/
├── src/
│   ├── pages/
│   │   └── AnalysisPage.tsx         # 改造（侧边栏 + 消息列表）
│   ├── components/
│   │   ├── analysis/
│   │   │   ├── AnalysisInput.tsx     # 保留
│   │   │   ├── EventTypeSelector.tsx # 保留
│   │   │   └── SimilarPrompt.tsx     # 保留
│   │   └── chat/                    # 新增目录
│   │       ├── MessageList.tsx
│   │       ├── MessageBubble.tsx
│   │       ├── ThinkingChain.tsx
│   │       └── SessionSidebar.tsx
│   ├── store/
│   │   └── chatStore.ts             # 新增
│   ├── services/
│   │   └── chatService.ts           # 新增
│   └── domain/
│       └── types.ts                  # 修改
```

## Complexity Tracking

无违反 Constitution 的情况。
