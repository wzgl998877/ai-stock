# Data Model: 个股分析界面展示优化与存档

**Feature Branch**: `005-analysis-ui-archive`
**Created**: 2025-04-25

## 实体定义

### E1: 分析记录 (Analysis Record)

扩展现有 `t_analysis_article` 表，用于存储个股分析的完整存档。

| 字段 | 类型 | 说明 | 来源 |
|------|------|------|------|
| article_id | String(32) PK | 唯一标识 | 已有 |
| title | String(50) | 分析标题 | 已有 |
| summary | String(200) | 分析摘要 | 已有 |
| content | Text | 完整 Markdown 内容 | 已有 |
| event_type | Enum | 固定 "other" | 已有 |
| raw_input | String(500) | 股票代码+名称 | 已有 |
| article_type | String(20) | 固定 "stock_analysis" | 已有（需启用写入） |
| analysis_data | JSON | 结构化分析数据（见 E1.1） | 已有（需启用写入） |
| status | String(20) | in_progress/completed/stopped | **新增列** |
| user_id | String(32) FK | 用户 ID | 已有 |
| create_time | DateTime | 创建时间 | 已有 |
| update_time | DateTime | 最后更新时间 | 已有 |
| deleted | Char(1) | 软删除标记 | 已有 |

**关联关系**：1:N → ArticleIndustry, 1:N → ArticleStock

#### E1.1: analysis_data JSON 结构

```json
{
  "mode": "full | quick",
  "agents": {
    "market_analyst": { "summary": "...", "completed_at": 1714036800000 },
    "fundamentals_analyst": { "summary": "...", "completed_at": 1714036860000 }
  },
  "debates": [
    { "speaker": "bull_researcher", "round": 1, "content": "..." }
  ],
  "decision": {
    "action": "买入", "target_price": 0, "confidence": 0.8,
    "risk_score": 0.3, "reasoning": "..."
  },
  "title": "...", "summary": "...", "industries": ["..."]
}
```

### E2: Agent 报告 (Agent Report)

`analysis_data.agents` 映射中的条目。

| 字段 | 类型 | 说明 |
|------|------|------|
| agent | String | Agent 标识（如 market_analyst） |
| summary | String | 分析摘要文本 |
| completed_at | Number | 完成时间戳（毫秒） |

### E3: 辩论事件 (Debate Event)

`analysis_data.debates` 数组元素。

| 字段 | 类型 | 说明 |
|------|------|------|
| speaker | String | 发言人标识 |
| round | Number | 轮次号 |
| content | String | 发言内容 |

### E4: 投资决策 (Investment Decision)

`analysis_data.decision` 对象。

| 字段 | 类型 | 说明 |
|------|------|------|
| action | String | 买入/卖出/持有 |
| target_price | Number | 目标价格 |
| confidence | Number | 置信度（0-1） |
| risk_score | Number | 风险评分（0-1） |
| reasoning | String | 决策依据 |

### E5: 阶段进度 (Phase Progress)

前端根据 `analysis_data` 计算，不独立存储。

| 字段 | 类型 | 说明 |
|------|------|------|
| total_phases | Number | 总阶段数（快速=1，深度=4） |
| completed_phases | Number | 已完成阶段数 |

### E6: 辩论轮次 (DebateRound) — 视图模型

| 字段 | 类型 | 说明 |
|------|------|------|
| round | Number | 轮次编号 |
| bull | DebateEvent \| null | 看多发言 |
| bear | DebateEvent \| null | 看空发言 |
| neutral | DebateEvent \| null | 中立派发言（仅风险辩论） |

### E7: 风险角色卡片 (RiskRoleCard) — 视图模型

| 字段 | 类型 | 说明 |
|------|------|------|
| agent | String | 角色标识 |
| label | String | 角色中文名 |
| content | String \| null | 完整辩论内容（多轮合并） |

## 状态机

### S1: 分析记录状态（持久化）

```
[开始分析] → in_progress
                ├── [全部阶段完成] → completed
                ├── [用户停止]     → stopped
                └── [异常中断]     → stopped
```

### S2: Agent 运行状态（前端内存态）

```
pending → running → done
                 → failed
```

### S3: 前端页面状态

```
idle → running → done → idle（重新分析）
       → error
viewMode（从记录进入，直接渲染结果）
```

## 数据库变更

### 新增列

| 表 | 列 | 类型 | 默认值 | 说明 |
|----|----|------|--------|------|
| t_analysis_article | status | VARCHAR(20) | "completed" | 分析状态 |

### 需打通的字段（已有列但未使用）

| 表 | 列 | 当前状态 | 改动 |
|----|----|----------|------|
| t_analysis_article | analysis_data | DB有列，Entity/Repo未映射 | 打通全链路 |
| t_analysis_article | article_type | DB有列，默认"event" | 写入时赋值"stock_analysis" |
