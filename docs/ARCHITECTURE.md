# 系统架构 (ARCHITECTURE)

> 最后更新: 2026-04-16 | 版本: v0.0.1

## 产品定位

个人投研辅助工具，**非**自动交易系统。界面与文案须体现「不构成投资建议」。

## 三模块闭环

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   模块一         │    │   模块二         │    │   模块三         │
│  AI事件分析      │───>│  行情数据展示    │<───│  策略监控        │
│  & 行业知识库    │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
  看懂新闻，沉淀认知       找到股票，看懂行情       监控自选股，发现信号
```

三模块互相打通：
- 模块一分析文章里的股票，点击直接跳到模块二看 K 线
- 模块二的自选股，在模块三自动监控缠论买卖点
- 模块三发现信号时，联动展示模块一的相关历史分析

## 技术架构

```
前端 (React 18 + Ant Design 5 + ECharts 5 + Zustand)
    ↓ HTTP API / SSE
后端 (Python FastAPI)
    ├── AI 分析服务 → OpenAI / DeepSeek API
    ├── 行情数据服务 → AKShare
    ├── 缠论计算引擎 → 纯 Python 实现
    └── 定时任务调度 → APScheduler
    ↓
数据层
    ├── MySQL（结构化数据）
    └── Redis（缓存）
```

## 后端分层

```
Router → Application → Domain → Infrastructure
```

- **Router**: 接口路由，参数校验
- **Application**: 业务流程编排
- **Domain**: 核心业务逻辑
- **Infrastructure**: 技术实现（数据库、缓存、外部 API）

原则：业务在 Domain，流程在 Application，技术在 Infrastructure。

## 前端分层

```
Page → Application → Service
```

- **Page**: 页面组件，UI 渲染
- **Application**: 页面级业务逻辑（Zustand Store）
- **Service**: API 调用封装

原则：所有 API 经 `services/`，页面不直连网络。

## 技术栈

| 层次 | 技术 |
|------|------|
| 前端框架 | React 18 + TypeScript |
| UI 组件库 | Ant Design 5 |
| 图表库 | ECharts 5 |
| 状态管理 | Zustand |
| 后端框架 | Python 3 + FastAPI |
| 数据源 | AKShare |
| 数据库 | MySQL |
| 缓存 | Redis |
| 大模型 | 统一抽象层（OpenAI / DeepSeek） |
| 任务调度 | APScheduler |
| 部署 | Docker Compose |

## 核心模块

### 模块一：AI 事件分析 & 行业知识库

- 流式输出（SSE）生成分析文章
- 五种事件类型：地缘政治 / 政策法规 / 财报季报 / 产业链分析 / 其他
- 知识库三视图：行业视图 / 时间线视图 / 股票视图
- 全文搜索、相似问题提醒、大事提醒

### 模块二：行情数据展示

- A 股行业板块列表与详情
- 个股 K 线图（支持缩放、均线叠加）、分时图
- 财务数据展示（营收、PE、PB、ROE 等）
- 关联模块一的分析文章

### 模块三：缠论策略监控

- 自选股管理
- 缠论核心要素：笔 / 线段 / 中枢
- 买卖点自动标注（一买/二买/三买 + 卖点）
- 信号报警（页面弹窗 + 可选邮件）

## 文档索引

| 文档 | 路径 | 说明 |
|------|------|------|
| 产品概览 | `docs/product-overview.md` | 三模块、用户路径与 MVP 边界 |
| 模块一 PRD | `docs/ai-analysis-prd.md` | AI 分析功能详细需求 |
| 模块二 PRD | `docs/market-data-prd.md` | 行情数据功能详细需求 |
| 模块三 PRD | `docs/strategy-monitor-prd.md` | 策略监控功能详细需求 |
| 集成说明 | `docs/INTEGRATION.md` | 外部依赖与部署配置 |
| 系统宪法 | `constitution.md` | 核心原则与架构红线 |
| 执行规则 | `rules/` | 后端/前端分层规范 |
