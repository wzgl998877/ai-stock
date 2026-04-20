
---

# 📘 ① Backend Core Rules（DDD + FastAPI + AI系统）

> 负责：系统基础架构 / 业务规范 / AI基础能力
> 不包含 Workflow 细节

---

## 一、总体架构（强制）

```text id="core1"
Router → Application → Domain → Infrastructure
```

---

## 二、目录结构（强制）

```text id="core2"
app/
 ├── routers/
 ├── application/
 │    ├── use_cases/
 │    ├── services/
 │    └── orchestrators/
 ├── domain/
 │    ├── entities/
 │    ├── value_objects/
 │    ├── services/
 │    └── repositories/
 ├── infrastructure/
 │    ├── db/
 │    ├── repositories/
 │    ├── ai/
 │    ├── search/
 │    ├── crawler/
 │    └── file_parser/
 ├── schemas/
 ├── core/
```

---

## 三、分层职责（强制）

### 3.1 Router

* 仅 HTTP 请求/响应
* 参数解析
* 返回结果
* ❌ 禁止业务逻辑

---

### 3.2 Application（用例层）

* 编排业务流程
* 调用 Domain
* 调用 Infrastructure
* 决定是否使用 AI 或 Workflow

---

### 3.3 Domain（核心业务层）

必须满足：

* ❌ 不依赖 FastAPI
* ❌ 不依赖 DB
* ❌ 不依赖 AI
* ❌ 不依赖 Workflow

---

### 包含：

* Entity
* Value Object
* Domain Service
* Repository Interface

---

### 3.4 Infrastructure（实现层）

负责：

* DB访问
* AI能力（LangChain 不强依赖，仅作为工具）
* 搜索能力
* 文件解析
* 网络抓取

---

## 四、AI模块规范（核心）

---

### 必须封装

```python
class AIService:
    async def stream(self, prompt): pass
```

---

### Prompt规范

* 模板化管理
* 禁止硬编码
* 禁止散落在 Node / UseCase 中

### Workflow 编排

多步骤 AI 流程（文档加载→搜索→总结等）使用 LangGraph Workflow，详见 **[rules/langgraph.md](./langgraph.md)**

---

## 五、搜索模块规范

```python
class SearchRepository:
    async def search(self, query): pass
```

---

支持：

* MySQL
* Elasticsearch
* 向量检索（RAG）

---

## 六、流式输出（SSE）

```text
data: xxx\n\n
```

---

## 七、数据库规范

* 所有 DB 操作必须在 Repository
* ORM（SQLAlchemy / SQLModel）
* JSON字段用于扩展

---

## 八、DTO规范

* Pydantic
* DTO 与 Domain 分离

---

## 九、异常处理

* Domain 抛业务异常
* Application 转 HTTP 异常
* 统一错误结构

---

## 十、日志规范

必须记录：

* AI调用
* 关键业务操作

---

## 十一、扩展性

必须支持：

* DB可替换
* Search可替换
* AI模型可切换
* RAG能力扩展

---

## 十二、开发流程（基础）

1. 定义输入输出
2. 设计 Domain
3. 实现 UseCase
4. 接入 Infrastructure
5. 暴露 Router

---

## 十三、核心原则

> 业务逻辑在 Domain
> 流程控制在 Application
> 技术实现在 Infrastructure

---

