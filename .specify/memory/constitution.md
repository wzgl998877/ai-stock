<!--
  Sync Impact Report
  ==================
  Version change: TEMPLATE (0.0.0) → 1.0.0
  Bump rationale: MINOR — initial population from project constitution.md;
    set to 1.0.0 to match the ratified source document.

  Modified principles:
    - (new) I. 三模块协同优先 (Three-Modules Synergy)
    - (new) II. 个人投研工具边界 (Research-Only)
    - (new) III. 简洁实用 (KISS & YAGNI)

  Added sections:
    - Core Principles (3 principles)
    - 技术约束 (Technical Constraints)
    - 治理 (Governance)

  Removed sections: N/A (first population)

  Templates requiring updates:
    - .specify/templates/plan-template.md  ✅ no changes needed
          (Constitution Check section already generic)
    - .specify/templates/spec-template.md  ✅ no changes needed
          (requirements format is generic)
    - .specify/templates/tasks-template.md ✅ no changes needed
          (task structure is generic)

  Follow-up TODOs: none
-->

# AI Stock 项目宪章 (Constitution)

本宪章定义了项目的核心原则、技术约束和治理规则，回答"**能不能做**"的问题。

---

## Core Principles

### I. 三模块协同优先 (Three-Modules Synergy)

产品由 **模块一（AI 事件分析 & 知识库）**、**模块二（行情数据展示）**、**模块三（策略监控）** 构成，功能与数据 MUST 能互相联动。

- 新增能力 MUST 标明归属模块，并说明与其它模块的**跳转或数据关联**（例如：分析中的股票代码 → K 线；自选股 → 监控信号；信号/个股 → 历史分析回溯）
- MVP 范围以 `docs/product-overview.md` 中的**核心跳转路径**与**阶段交付**为准，MUST NOT 做该产品边界中明确排除的能力（自动交易、Level 2、多市场等）

**理由**：三模块闭环是产品核心价值，任何孤岛式功能都会削弱用户投研体验。

### II. 个人投研工具边界 (Research-Only)

本产品是**辅助研究工具**，不是券商、投顾或自动交易系统。

- **MUST NOT** 实现自动下单、实盘交易接口、代客理财类能力
- 行情与信号 MUST 体现**数据源延迟**与**算法简化**（如 AKShare、缠论程序化实现的局限）
- 涉及预测、信号、买卖点等表述时，MUST 保留**不构成投资建议**语义，MUST NOT 承诺收益

**理由**：合规与风险控制底线；超出个人投研工具边界的功能会引入法律和监管风险。

### III. 简洁实用 (KISS & YAGNI)

- 代码修改 MUST 遵循最小变更原则，MUST NOT 引入不必要的重构
- MUST NOT 为假设的未来需求提前设计，按当前业务需求实现
- 三行相似代码优于一个过早的抽象
- MUST 复用 Ant Design、既有服务封装与领域抽象，MUST NOT 重复造轮子

**理由**：个人投研工具追求迭代速度和维护简单性，过度设计会增加不必要的复杂度。

---

## 技术约束 (Technical Constraints)

### 技术栈

- **前端**：React 18 + TypeScript + Ant Design 5 + ECharts 5 + **Zustand**
- **后端**：Python 3 + **FastAPI**
- **数据**：**MySQL**（主库）+ **Redis**（缓存/计算结果）；A 股数据 **AKShare**
- **大模型**：MUST 经统一抽象层接入（如 OpenAI / DeepSeek 兼容接口），**MUST NOT** 在业务层散落直连 SDK

> 持久化访问 MUST 经 **Repository**，主库以本宪章为准采用 **MySQL**；若 `rules/backend.md` 与宪章冲突，以本宪章为准。

### 架构红线

- **MUST NOT 跨层调用**：后端 MUST 遵守 Router → Application → Domain → Infrastructure；Router **MUST NOT** 直接访问数据库或调用大模型；Domain **MUST NOT** 依赖 FastAPI、**MUST NOT** 直接访问数据库与 AI
- **MUST NOT 前端绕开 Service**：页面与组件 **MUST NOT** 直接使用 `fetch`；所有 HTTP 调用 MUST 集中在 `services/`
- **MUST NOT 泄露密钥**：API Key、数据库密码等 MUST 仅来自环境变量（如 `.env`），**MUST NOT** 写入源码或提交仓库
- **流式输出 MUST 成对实现**：后端 SSE 格式 MUST 符合约定（`data: ...\n\n`）；前端 MUST 具备实时输出、滚动、停止与 loading（见 `rules/`）

### 数据约束

- 关键金额与比率在 Python 侧 MUST 使用 **`Decimal`** 等合适类型，**MUST NOT** 用 `float` 承载核心业务数值
- 所有数据库操作 MUST 在 **Repository** 内完成；JSON 可用于扩展字段，核心字段 MUST 可查询、可迁移
- Prompt 与提示词 MUST **模板化管理**，MUST NOT 多处硬编码副本

---

## Governance

### 变更流程

1. **理解上下文**：修改前 MUST 阅读相关 PRD（`docs/ai-analysis-prd.md`、`docs/market-data-prd.md`、`docs/strategy-monitor-prd.md`）及对应代码
2. **对齐分层**：前后端分别 MUST 遵守 `rules/backend.md`、`rules/frontend.md`
3. **本地验证**：MUST 按仓库约定执行构建、类型检查与关键路径验证（前后端脚本以项目落地后的 `README.md` 为准）

### Code Review 清单

- [ ] 是否违反「个人投研工具」或模块边界？
- [ ] 后端是否出现 Router/Domain 直连 DB 或 AI？
- [ ] 前端是否出现页面/组件直连 `fetch`？
- [ ] 流式/SSE 与前端流式体验是否一致？
- [ ] 日志与配置是否避免泄露密钥与敏感请求体？

### 优先级

- 本宪章优先级高于个人编码习惯，所有代码变更 MUST 符合宪章规定
- 宪章修改 MUST 记录修改原因和影响范围
- **详细执行规则见**：[rules/](./rules/) 目录

---

**Version**: 1.0.0 | **Ratified**: 2026-04-16 | **Last Amended**: 2026-04-16
