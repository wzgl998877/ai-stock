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
- 作为静态数据维护在 `data/industries.json`
- 包含行业名称

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

### analysis_articles 表

| Index | Columns | Type | Purpose |
|-------|---------|------|---------|
| idx_created_at | created_at DESC | B-Tree | 时间线视图倒序 |
| idx_event_type | event_type | B-Tree | 按类型筛选 |
| idx_user_id | user_id | B-Tree | 多用户隔离 |
| ft_search | title, summary, content | FULLTEXT (ngram) | 全文搜索 |

### article_industries 表

| Index | Columns | Type | Purpose |
|-------|---------|------|---------|
| PK | article_id, industry_name | PRIMARY | 复合主键 |
| idx_industry | industry_name | B-Tree | 按行业筛选文章 |

### event_reminders 表

| Index | Columns | Type | Purpose |
|-------|---------|------|---------|
| idx_event_date | event_date | B-Tree | 按日期查询 |
| idx_status_date | status, event_date | B-Tree | 调度查询优化 |
| idx_user_id | user_id | B-Tree | 多用户隔离 |

## DDL (参考)

```sql
CREATE TABLE analysis_articles (
    id CHAR(36) PRIMARY KEY,
    title VARCHAR(50) NOT NULL,
    summary VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    event_type ENUM('geopolitical','policy','earnings','supply_chain','other') NOT NULL,
    raw_input VARCHAR(500) NOT NULL,
    industry_tags JSON,
    mentioned_stocks JSON,
    chain_table JSON,
    user_id VARCHAR(50) NOT NULL DEFAULT 'default',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FULLTEXT INDEX ft_search (title, summary, content) WITH PARSER ngram,
    INDEX idx_created_at (created_at DESC),
    INDEX idx_event_type (event_type),
    INDEX idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE article_industries (
    article_id CHAR(36) NOT NULL,
    industry_name VARCHAR(30) NOT NULL,
    chain_level INT,
    PRIMARY KEY (article_id, industry_name),
    INDEX idx_industry (industry_name),
    FOREIGN KEY (article_id) REFERENCES analysis_articles(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE event_reminders (
    id CHAR(36) PRIMARY KEY,
    title VARCHAR(100) NOT NULL,
    event_date DATE NOT NULL,
    industry_tags JSON,
    status ENUM('pending','reminded','archived') NOT NULL DEFAULT 'pending',
    remind_3day_sent BOOLEAN NOT NULL DEFAULT FALSE,
    remind_today_sent BOOLEAN NOT NULL DEFAULT FALSE,
    user_id VARCHAR(50) NOT NULL DEFAULT 'default',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_event_date (event_date),
    INDEX idx_status_date (status, event_date),
    INDEX idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```
