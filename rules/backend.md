# Backend Rules（DDD + FastAPI + MySQL）

> 适用于：AI分析 / 知识库 / 搜索 / RAG系统  
> 架构：简化DDD + Clean Architecture  

---

## 一、总体架构（强制）

Router → Application → Domain → Infrastructure

---

## 二、目录结构（强制）

app/
 ├── routers/
 ├── application/
 ├── domain/
 │    ├── entities/
 │    ├── value_objects/
 │    ├── services/
 │    └── repositories/
 ├── infrastructure/
 │    ├── db/
 │    ├── repositories/
 │    ├── ai/
 │    └── search/
 ├── schemas/
 ├── core/

---

## 三、分层职责（强制）

### 3.1 Router

- 仅处理 HTTP 请求/响应
- 参数解析 + 返回
- 禁止业务逻辑
- 禁止访问数据库

---

### 3.2 Application（用例层）

- 编排业务流程
- 调用 Domain
- 调用 Repository接口
- 不直接访问数据库

---

### 3.3 Domain（核心业务层）

必须满足：

- 不依赖 FastAPI
- 不依赖数据库
- 不调用 AI

#### 包含：

- Entity（实体）
- Value Object（值对象）
- Domain Service（领域服务）
- Repository接口定义

---

### 3.4 Infrastructure（实现层）

负责：

- 数据库访问
- AI能力
- 搜索能力

---

## 四、Repository规范

### 接口定义（Domain）

```python
class ArticleRepository:
    async def get(self, id): pass
```

### 实现（Infrastructure）

```python
class MySQLArticleRepository(ArticleRepository):
    ...
```

------

## 五、AI模块规范（核心）

### 禁止

- Domain 调用 AI
- Router 调用 AI
- 直接调用模型 API

### 必须封装

```python
class AIService:
    async def stream(self, prompt): pass
```

### Prompt规范

- 模板化管理
- 禁止硬编码

### LangGraph Agent

当业务需要多步骤 AI 编排（文档加载 → 搜索 → 总结等）时，引入 LangGraph。

- 详细规则见 **[rules/langgraph.md](./langgraph.md)**
- LangGraph 定位为 Infrastructure 层组件，Node 中调用 LLM 仍须通过 AIService

------

## 六、搜索模块规范

### 抽象接口

```python
class SearchRepository:
    async def search(self, query): pass
```

### 可替换实现

- MySQL
- Elasticsearch
- 向量搜索（RAG）

------

## 七、流式输出（SSE）

格式必须：

data: xxx\n\n

------

## 八、数据库规范

- 所有 DB 操作必须在 Repository
- 使用 ORM（SQLAlchemy / SQLModel）
- JSON字段用于扩展

------

## 九、DTO规范

- 使用 Pydantic
- DTO 与 Domain 分离

------

## 十、异常处理

- 统一异常处理
- Domain 抛业务异常
- Application 转换为 HTTP 响应

------

## 十一、日志规范

必须记录：

- AI调用
- 关键业务操作

------

## 十二、扩展性

必须支持：

- 关系型主库可替换（须保持 Repository 抽象；实现以宪章约定为准）
- 数据库搜索 → Elasticsearch
- AI模型切换

------

## 十三、开发流程

1. 定义需求（输入/输出）
2. 设计 Domain
3. 实现 UseCase（Application）
4. 接入 Repository / AI
5. 提供接口（Router）

------

## 十四、核心原则

业务逻辑在 Domain
流程控制在 Application
技术实现放在 Infrastructure

