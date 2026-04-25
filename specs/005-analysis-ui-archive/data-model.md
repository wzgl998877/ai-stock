# Data Model: 个股分析界面展示优化与存档

**Feature Branch**: `005-analysis-ui-archive`
**Date**: 2025-04-25

## Entities

### AgentCompletedAt (Store 扩展)

| Field | Type | Description |
|-------|------|-------------|
| agent | string | Agent 标识（如 "market_analyst"） |
| timestamp | number | 完成时间戳（ms），由前端在 agent_status 事件 status="done" 时记录 |

**Relationship**: 与 `agentStatuses` 一对一，共享同一 key

### TextHighlight (工具层)

| Field | Type | Description |
|-------|------|-------------|
| pattern | RegExp | 数字匹配正则（百分比、价格） |
| style | object | 高亮样式（color: #533afd, fontWeight: 600） |

**Note**: 纯前端渲染工具，不持久化

### DebateRound (视图模型)

| Field | Type | Description |
|-------|------|-------------|
| round | number | 轮次编号 |
| bull | DebateEvent \| null | 看多研究员发言 |
| bear | DebateEvent \| null | 看空研究员发言 |
| neutral | DebateEvent \| null | 中立派发言（仅风险辩论） |

**Relationship**: 从 `debates` 数组按 round 聚合生成，纯前端派生视图

### RiskRoleCard (视图模型)

| Field | Type | Description |
|-------|------|-------------|
| agent | string | 角色标识（如 "risky_debator"） |
| label | string | 角色中文名（如 "激进派"） |
| content | string \| null | 该角色的完整辩论内容（多轮合并） |
| status | string | 当前状态（pending/running/done/failed） |
| completedAt | number \| undefined | 完成时间戳 |

**Relationship**: 交易决策官内容来自 `decision.reasoning`，其余角色来自 `debates` 按 speaker 过滤

## State Transitions

### Agent Status

```
pending → running → done
                  → failed
```

- `pending → running`: 收到 `agent_status` 事件 `status="running"`
- `running → done`: 收到 `agent_status` 事件 `status="done"`，同时记录 `agentCompletedAt`
- `running → failed`: 收到 `agent_status` 事件 `status="failed"`，同时记录 `agentCompletedAt`

### Analysis Phase

```
analysts → debate → trader → risk → (done)
```

- 阶段切换由 `agent_status` 事件中的 `phase` 字段驱动
- 快速模式仅经历 `analysts` 阶段

### Analysis State

```
idle → running → done
               → error
```

- `idle → running`: 用户点击"开始分析"
- `running → done`: 收到 `done` 事件或用户点击"停止分析"
- `running → error`: 收到 `error` 事件或网络异常
- `done/error → idle`: 用户点击"重新分析"并确认
