# Data Model: AI 事件分析 & 行业知识库

**Feature**: 001-ai-event-analysis
**Date**: 2026-04-16

## Entities

### 1. AnalysisArticle (分析文章)

用户保存的 AI 分析文章，是知识库的核心实体。

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| id | UUID | yes | 主键 | 自动生成 |
| title | String(50) | yes | AI 生成标题 | ≤15字中文，用户可编辑 |
| summary | String(200) | yes | AI 生成摘要 | ≤80字中文，2句话结论导向 |
| content | Text | yes | 分析正文 | Markdown 格式，六段/七段结构 |
| event_type | Enum | yes | 事件类型 | geopolitical/policy/earnings/supply_chain/other |
| raw_input | String(500) | yes | 用户原始输入 | 最少10字 |
| industry_tags | JSON | no | AI 提取的行业标签 | 申万一级行业列表 |
| mentioned_stocks | JSON | no | 提及的股票列表 | [{code, name}] 格式 |
| chain_table | JSON | no | 产业链传导表 | 仅 supply_chain 类型 |
| user_id | String(50) | yes | 用户标识 | 预留多用户 |
| created_at | DateTime | yes | 创建时间 | 自动填充 |
| updated_at | DateTime | yes | 更新时间 | 自动更新 |

**Relationships**: 一篇文章关联多个 IndustryTag (多对多，通过 article_industries 表)

### 2. EventReminder (大事提醒)

用户手动录入的未来重要事件。

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| id | UUID | yes | 主键 | 自动生成 |
| title | String(100) | yes | 事件名称 | 必填 |
| event_date | Date | yes | 事件日期 | 必须是未来日期 |
| industry_tags | JSON | no | 关联行业 | 申万一级行业列表 |
| status | Enum | yes | 状态 | pending/reminded/archived |
| remind_3day_sent | Boolean | yes | 3天前提醒是否已发 | 默认 false |
| remind_today_sent | Boolean | yes | 当天提醒是否已发 | 默认 false |
| user_id | String(50) | yes | 用户标识 | 预留多用户 |
| created_at | DateTime | yes | 创建时间 | 自动填充 |
| updated_at | DateTime | yes | 更新时间 | 自动更新 |

### 3. ArticleIndustry (文章-行业关联)

多对多关联表。

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| article_id | UUID | yes | 文章 ID (FK) |
| industry_name | String(30) | yes | 行业名称（申万一级） |
| chain_level | Integer | no | 传导层级（仅产业链分析） |

**Note**: 使用复合主键 (article_id, industry_name)

## Value Objects

### EventType (事件类型枚举)

```
GEO_POLITICAL = "geopolitical"    # 地缘政治
POLICY = "policy"                 # 政策法规
EARNINGS = "earnings"             # 财报季报
SUPPLY_CHAIN = "supply_chain"     # 产业链分析
OTHER = "other"                   # 其他
```

### ReminderStatus (提醒状态枚举)

```
PENDING = "pending"      # 待触发
REMINDED = "reminded"    # 已提醒
ARCHIVED = "archived"    # 已归档（过期）
```

### IndustryTag (行业标签)

- 基于申万31个一级行业分类
- 作为静态数据维护在 `domain/constants.py`
- 包含行业名称和可选的行业代码

### StockReference (股票引用)

```
{
  "code": "600519",    # 股票代码
  "name": "贵州茅台",   # 股票名称
  "industry": "食品饮料" # 所属行业
}
```

## State Transitions

### Article Lifecycle

```
[用户输入] → [AI 分析中] → [结果展示] → [用户确认标签] → [保存到知识库]
                                    ↓
                              [不保存/丢弃]
```

### Reminder Lifecycle

```
[创建提醒] → [pending] → [3天前提醒] → [当天提醒] → [过期归档 archived]
                 ↓                        ↓
           remind_3day_sent=true    remind_today_sent=true
```

## Indexes

- `analysis_articles`: created_at (倒序), event_type, user_id
- `analysis_articles`: GIN 索引 on content (全文搜索), industry_tags, mentioned_stocks
- `article_industries`: industry_name (用于按行业筛选)
- `event_reminders`: event_date, status, user_id
- `event_reminders`: (status, event_date) 复合索引（用于调度查询）
