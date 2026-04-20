
---

#  Workflow Rules（LangGraph 多步骤AI编排）

> 负责：多步骤AI分析 / RAG / 搜索推理 /
> 基于：LangGraph

---

## 一、架构定位（强制）

Workflow 属于：

> 👉 Infrastructure 层的“流程执行引擎”

---

### 分层关系

```text id="wf1"
Router → Application → Domain → Infrastructure → Workflow
```

---

## 二、禁止规则（非常重要）

❌ 禁止：

* Domain 依赖 Workflow
* Router 直接调用 Graph
* Workflow 直接访问 DB
* Workflow 内直接调用 LLM HTTP API
* Workflow 中拼接 Prompt

---

## 三、目录结构（强制）

```text id="wf2"
app/infrastructure/workflow/
 ├── graph/
 ├── nodes/
 ├── tools/
 ├── state/
 └── prompts/
```

---

## 四、State 规范（强制）

### ⭐ 三层结构（必须）

```text id="wf3"
InputState → WorkingState → OutputState
```

---

### InputState

```python
class InputState(TypedDict):
    source: str
    event_type: str
```

---

### WorkingState

```python
class WorkingState(TypedDict):
    raw_text: str
    search_results: list[str]
    context: str
```

---

### OutputState

```python
class OutputState(TypedDict):
    title: str
    summary: str
    analysis: str
    industries: list[str]
    error: str | None
```

---

## 五、Node 规范（强制）

### 职责

* 调用 Service
* 更新 State
* 不写业务逻辑

---

### 标准格式

```python
async def search_node(state):
    results = await search_service.search(state["source"])
    return {"search_results": results}
```

---

### 禁止

* ❌ LLM调用写死
* ❌ DB操作
* ❌ Prompt拼接
* ❌ 业务逻辑组合

---

## 六、Tool 规范

Tool = 原子能力

* search
* crawl
* file parse

---

## 七、Graph 规范

```text id="wf4"
input → classify → search → retrieve → reasoning → output
```

---

必须：

* 有 END
* 覆盖 error path
* 支持条件分支

---

## 八、AI调用规范

Workflow 中 LLM 调用必须：

```text id="wf5"
Node → AIService → LLM
```

❌ 禁止直接 HTTP 调用模型

---

## 九、流式输出（SSE）

Workflow 输出必须映射为：

```text
data: xxx\n\n
```

---

## 十、日志规范（增强）

必须记录：

* node_name
* state_change
* workflow_id

---

## 十一、依赖管理

### 引入

* `langgraph`（Graph 编排核心）
* `langchain-core`（基础抽象，如 @tool 装饰器）

### 禁止引入

* `langchain`（完整包，过重）
* `langchain-community`（大量不需要的集成）
* `langchain-experimental`（实验性功能，不稳定）

> 只按需引入轻量子包

---

## 十二、Prompt规范

* 全部集中管理
* 不允许 Node 内拼 Prompt
* 分离 system / template

---

## 十三、开发流程

1. 设计 State
2. 拆 Node
3. 设计 Graph
4. 接入 Service
5. 接 UseCase
6. 接 Router

---

## 十四、核心原则

> Workflow 是“流程执行器”，不是业务系统

---

## 🚀 最终效果（你现在的架构）

```text id="final"
DDD Core System + AI能力
        +
Workflow Engine（复杂AI流程）
```

---