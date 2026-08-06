# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 语言要求

**始终使用中文回答所有问题和进行所有交流。**

## 📖 编码前必读（重要！）

执行任何代码修改前，必须按顺序阅读以下文档：

1. **[Constitution（系统宪法）](../constitution.md)** — 理解"**能不能做**"
   （核心原则、技术约束、架构红线）

2. **[Rules（执行规则）](../rules/)** — 理解"**怎么做才对**"
   - [后端分层与架构](../rules/backend.md)
   - [前端分层与交互](../rules/frontend.md)

3. **[产品概览](./product-overview.md)** — 理解三模块、用户路径与 MVP 边界

4. **各模块 PRD**（按需深入）
   - [模块一：AI 分析](./ai-analysis-prd.md)
   - [模块二：行情数据](./market-data-prd.md)
   - [模块三：策略监控](./strategy-monitor-prd.md)

## ⚖️ 规则冲突优先级

当规则冲突时，按以下顺序执行：

1. `constitution.md`
2. `rules/*`
3. `CLAUDE.md`

## 🛠 技术栈

- **前端**：React 18 + TypeScript + Ant Design 5 + ECharts 6 + Zustand
- **后端**：Python 3 + FastAPI
- **数据**：AKShare（A 股数据）、MySQL、Redis
- **大模型**：统一抽象层，支持 OpenAI / DeepSeek 等兼容接口
- **任务与部署**：APScheduler、Docker Compose（以仓库实际配置为准）

## 🏗 架构要点

- **三模块闭环**：模块一（AI 与知识库）→ 模块二（行情与个股）← 模块三（缠论信号与监控），跳转与数据须可联动
- **后端分层**：Router → Application → Domain → Infrastructure（业务在 Domain，流程在 Application，技术在 Infrastructure）
- **前端分层**：Page → Application → Service；**所有 API** 经 `services/`，页面不直连网络
- **AI 与流式**：大模型须封装调用；分析结果须支持流式输出（SSE + 前端 EventSource 等）
- **产品定位**：个人投研辅助工具，**非**自动交易系统；界面与文案须体现「不构成投资建议」

## 📦 构建与运行

> 以下命令在前后端目录落地后使用；若当前仓库尚未初始化工程，以实现后的 `README.md` 为准。

```bash
# 后端（示例：在项目根目录或 backend 目录下）
# pip install -r requirements.txt
# uvicorn app.main:app --reload --host 0.0.0.0 --port 18000

# 前端（示例：在 frontend 目录下）
# npm install
# npm run dev
```

```bash
# 容器编排（若已提供）
# docker compose up -d
```

## 📚 详细文档索引

- **产品总览**：[product-overview.md](./product-overview.md)
- **用户使用说明**：[README.md](../README.md)

**最后更新**: 2026-04-16
