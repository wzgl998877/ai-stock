# LangGraph Agent 规则

> 适用于：多步骤 AI 编排（文档加载 → 搜索 → 总结 → 结构化输出）
> 框架：LangGraph（Stateful Agent Orchestration）

---

## 一、架构定位（强制）

LangGraph 是 **Infrastructure 层组件**，负责多步骤 AI 工作流的编排。

### 1.1 分层归属

```
Router          → HTTP 入口，调用 UseCase
Application     → UseCase 编排业务流程，决定何时使用 Agent
Domain          → 纯业务逻辑，不感知 LangGraph
Infrastructure  → LangGraph Agent 实现（Graph / Node / Tool）
```

### 1.2 禁止

- Domain 层直接依赖 LangGraph
- Router 层直接调用 LangGraph
- 在 LangGraph Node 中绕过 AIService 直接调用 LLM HTTP 接口
- LangGraph 内部硬编码 Prompt（须走模板化管理）

### 1.3 核心原则

**Agent 是手段，不是架构**。LangGraph 编排的工作流最终产出的仍是领域对象（AnalysisArticle / EventAnalysis），不因为引入 Agent 而改变业务模型。

---

## 二、目录结构（强制）

```
app/
 └── infrastructure/
      └── agent/
           ├── __init__.py
           ├── graphs/              # Graph 定义（每个场景一个）
           │    ├── analyze_document.py   # 文档/链接分析 Graph
           │    └── ...
           ├── nodes/               # Node 实现（每个节点一个文件）
           │    ├── document_loader.py    # 加载文档（URL/PDF/文本）
           │    ├── text_splitter.py      # 文本分块
           │    ├── retriever.py          # 知识库检索
           │    ├── summarizer.py         # LLM 总结
           │    └── ...
           ├── tools/               # Tool 定义（供 Agent 调用）
           │    ├── web_search.py         # 网络搜索
           │    ├── web_scraper.py        # URL 爬取
           │    ├── file_parser.py        # 文件解析
           │    └── ...
           ├── state/               # State Schema 定义
           │    ├── document_state.py
           │    └── ...
           └── prompts/             # Agent 相关 Prompt 模板
                ├── agent_system.py
                └── ...
```

> `infrastructure/ai/prompts/` 仍保留现有事件分析 Prompt；Agent 专属 Prompt 放在 `infrastructure/agent/prompts/`。

---

## 三、State 设计规范（强制）

### 3.1 定义原则

- State 必须使用 **TypedDict** 定义，字段类型明确
- State 是 **数据载体**，不包含业务逻辑
- 每个 Graph 有独立的 State 定义

### 3.2 标准模板

```python
from typing import TypedDict, Optional, Annotated
from operator import add

class DocumentAnalysisState(TypedDict, total=False):
    # 输入
    source: str                          # 原始输入（URL/文件路径/文本）
    event_type: str                      # 事件类型

    # 中间状态
    raw_text: str                        # 加载后的原始文本
    chunks: list[str]                    # 分块结果
    search_results: list[str]            # 检索结果
    messages: Annotated[list, add]       # 累积的 LLM 对话消息

    # 输出
    analysis_content: str                # 分析正文（Markdown）
    title: str                           # 标题
    summary: str                         # 摘要
    industries: list[str]                # 关联行业
    error: Optional[str]                 # 错误信息
```

### 3.3 命名规范

- State 类名以 `State` 结尾：`DocumentAnalysisState`、`ResearchState`
- 字段使用 snake_case
- 区分**输入字段**（由调用方传入）和**输出字段**（由 Node 填充）

---

## 四、Node 设计规范（强制）

### 4.1 单一职责

每个 Node **只做一件事**：

| Node | 职责 | 输入 | 输出 |
|------|------|------|------|
| `document_loader` | 加载文档 | `source` | `raw_text` |
| `text_splitter` | 文本分块 | `raw_text` | `chunks` |
| `retriever` | 知识库检索 | `chunks` | `search_results` |
| `summarizer` | LLM 总结 | `messages` | `analysis_content` |

### 4.2 函数签名

```python
async def document_loader(state: DocumentAnalysisState) -> dict:
    """加载文档，返回需要更新的 State 字段"""
    source = state["source"]
    # ... 加载逻辑
    return {"raw_text": text}  # 只返回要更新的字段
```

- Node 函数必须是 **async**
- 接收完整 State，返回**部分更新**的 dict
- 禁止在 Node 内部修改全局状态或产生副作用（写数据库等）

### 4.3 错误处理

Node 内部捕获异常，返回 `error` 字段：

```python
async def document_loader(state: DocumentAnalysisState) -> dict:
    try:
        text = await load(state["source"])
        return {"raw_text": text}
    except Exception as e:
        return {"error": f"文档加载失败: {str(e)}"}
```

---

## 五、Tool 设计规范（强制）

### 5.1 定义原则

Tool 是 Node 可调用的**原子能力**，与 Node 的区别：

- **Tool**：无状态的原子操作（搜索一次、爬取一个 URL）
- **Node**：编排一个或多个 Tool，决定 Graph 中的一个步骤

### 5.2 Tool 模板

```python
from langchain_core.tools import tool

@tool
async def web_scraper(url: str) -> str:
    """爬取指定 URL 的正文内容。

    Args:
        url: 要爬取的网页地址

    Returns:
        网页正文文本
    """
    # 实现逻辑，复用 infrastructure 层的 httpx 客户端
    ...
```

### 5.3 禁止

- Tool 中直接访问数据库（须经 Repository）
- Tool 中硬编码 API Key 或密钥
- Tool 返回非结构化的原始数据（须做基本清洗）

---

## 六、Graph 设计规范（强制）

### 6.1 定义模板

```python
from langgraph.graph import StateGraph, END

def build_document_analysis_graph() -> CompiledGraph:
    graph = StateGraph(DocumentAnalysisState)

    # 添加节点
    graph.add_node("load", document_loader)
    graph.add_node("split", text_splitter)
    graph.add_node("retrieve", retriever)
    graph.add_node("analyze", summarizer)

    # 定义边
    graph.set_entry_point("load")
    graph.add_edge("load", "split")
    graph.add_conditional_edges("load", route_by_source, {
        "url": "scrape",
        "text": "analyze",
        "error": END,
    })
    graph.add_edge("analyze", END)

    return graph.compile()
```

### 6.2 边的设计

- **静态边**（`add_edge`）：无条件的顺序流转
- **条件边**（`add_conditional_edges`）：根据 State 中的字段决定下一步
- 每个 Graph 必须有明确的 **END** 节点
- 条件边必须覆盖所有可能的分支（含 error 分支）

### 6.3 命名规范

- Graph 构建函数以 `build_` 开头：`build_document_analysis_graph`
- Node 名称使用 snake_case：`document_loader`
- Graph 名称体现业务场景：`document_analysis`、`research`

---

## 七、与现有 AIService 的关系（强制）

### 7.1 职责划分

```
AIService（现有）          → 单轮 LLM 调用（stream_chat / generate）
LangGraph Agent（新增）    → 多步骤编排（加载→搜索→总结）
```

### 7.2 调用关系

LangGraph Node 中需要调用 LLM 时，**通过 AIService 间接调用**：

```python
# ✅ 正确：Node 通过 AIService 调用 LLM
async def summarizer(state: DocumentAnalysisState) -> dict:
    ai_service = get_ai_service()  # 从依赖注入获取
    system_prompt = build_summary_prompt(state["event_type"])
    chunks = []
    async for chunk in ai_service.stream_chat(system_prompt, state["raw_text"]):
        chunks.append(chunk)
    return {"analysis_content": "".join(chunks)}

# ❌ 禁止：Node 中直接用 httpx 调 LLM
async def summarizer(state):
    async with httpx.AsyncClient() as client:
        resp = await client.post("https://api.deepseek.com/v1/chat/completions", ...)
```

### 7.3 LLM 配置

- 模型选择、API Key、Base URL 等配置 **统一走 `core/config.py`**
- LangGraph 不单独维护 LLM 配置
- 禁止在 LangGraph 代码中硬编码模型名称或 API 地址

---

## 八、流式输出对接（强制）

### 8.1 对接原则

LangGraph 的流式输出必须 **复用现有 SSE 链路**：

```
LangGraph Graph.stream()
  → Application UseCase 适配
    → FastAPI StreamingResponse (SSE: data: xxx\n\n)
      → 前端 fetch ReadableStream 解析
```

### 8.2 UseCase 适配层

```python
# application/use_cases/analyze_document.py
class AnalyzeDocumentUseCase:
    async def execute(self, event_type: str, source: str):
        graph = build_document_analysis_graph()
        initial_state = {"source": source, "event_type": event_type}

        async for event in graph.astream(initial_state):
            # 将 LangGraph 事件转换为现有 SSE 格式
            if "analyze" in event:
                content = event["analyze"].get("analysis_content", "")
                yield {"type": "content", "data": content}
            # ... 其他事件类型映射
```

### 8.3 前端无感

前端 SSE 解析逻辑 **不需要修改**，仍然处理 `content / title / summary / industries / done` 事件。

---

## 九、Prompt 管理（强制）

### 9.1 模板位置

- 现有事件分析 Prompt → `infrastructure/ai/prompts/`（不变）
- Agent 专属 Prompt → `infrastructure/agent/prompts/`

### 9.2 模板规范

```python
# infrastructure/agent/prompts/agent_system.py

DOCUMENT_ANALYSIS_SYSTEM = """你是一个专业的财经事件分析师。

## 任务
基于以下参考资料，分析事件对 A 股市场的影响。

## 参考资料
{context}

## 输出格式
{output_format}
"""

def build_agent_prompt(context: str, event_type: str) -> str:
    output_format = get_output_format(event_type)
    return DOCUMENT_ANALYSIS_SYSTEM.format(
        context=context,
        output_format=output_format,
    )
```

- 所有 Prompt 必须以 **常量 + 构建函数** 的形式存在
- 禁止在 Node / Tool 中拼接 Prompt 字符串
- Agent Prompt 可复用 `infrastructure/ai/prompts/` 中的输出格式定义

---

## 十、依赖管理

### 10.1 必需依赖

```
langgraph>=0.2              # Graph 编排核心
langchain-core>=0.3         # 基础抽象（@tool 装饰器等）
```

### 10.2 禁止引入

- `langchain`（完整包，过重）
- `langchain-community`（包含大量不需要的集成）
- `langchain-experimental`（实验性功能，不稳定）

> 只引入 `langgraph` 和 `langchain-core`，按需引入其他轻量子包。

---

## 十一、开发流程

1. 定义需求（输入是什么？输出是什么？需要几步？）
2. 设计 State Schema（`state/` 下新建）
3. 实现 Tool（`tools/` 下，按需）
4. 实现 Node（`nodes/` 下，编排 Tool）
5. 组装 Graph（`graphs/` 下，定义边和条件）
6. 创建 UseCase（Application 层，对接 SSE）
7. 暴露 Router（HTTP 入口）

---

## 十二、测试规范

### 12.1 必须测试

- 每个 Node 的独立行为（输入 State → 输出 dict）
- Graph 的完整流转（mock LLM 调用）
- 条件边的分支覆盖

### 12.2 禁止

- 测试中调用真实 LLM API
- 测试中依赖外部网络（URL 爬取等须 mock）

---

## 十三、核心原则

**Agent 服务于业务，不是业务服务于 Agent。**

- LangGraph 是 Infrastructure 层的一个工具，不是架构的核心
- 领域模型（Article / EventAnalysis）不因 Agent 引入而改变
- 简单的单轮 LLM 调用继续走 AIService，不要为了用 Agent 而用 Agent
