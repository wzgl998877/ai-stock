# Data Model: AI 事件分析 & 行业知识库

**Feature**: 001-ai-event-analysis
**Date**: 2026-04-16
**Updated**: 2026-04-16（同步 `docs/FEATURES/AI_Analysis/ai-analysis.ddl.md` DDL）

## 全局约定

- **主键**: `VARCHAR(32)` UUID，不含连字符
- **软删除**: 所有表含 `deleted CHAR(1) DEFAULT '0'`，查询须过滤
- **审计字段**: 所有表含 `create_time`、`update_time`、`create_user`、`update_user`
- **字符集**: `utf8mb4_unicode_ci`

## ER 关系概览

```
t_user ──1:N── t_analysis_article
                  ├── N:M ── t_article_industry ── t_industry
                  └── N:M ── t_article_stock ── t_stock

t_user ──1:N── t_event_reminder
t_user ──1:N── t_chat_session ──1:N── t_chat_message

t_stock ── N:M ── t_stock_industry ── t_industry
```

## Entities

### 1. t_user (用户表)

用户主表，初期单用户，预留多用户扩展。

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| user_id | VARCHAR(32) PK | yes | 用户编号 |
| user_account | VARCHAR(32) | yes | 登录账号 |
| user_name | VARCHAR(32) | no | 用户名 |
| password | VARCHAR(128) | yes | 登录密码（加密存储） |
| nick_name | VARCHAR(100) | no | 昵称 |
| icon_url | VARCHAR(255) | no | 头像地址 |
| gender | CHAR(1) | no | 性别（0=未知,1=男,2=女） |
| mobile | VARCHAR(35) | no | 手机号码 |
| user_type | CHAR(1) | no | 用户类型（0=普通,1=管理员） |
| status | CHAR(1) | yes | 状态（0=正常,1=停用） |
| last_login | DATETIME | no | 上次登录时间 |

### 2. t_industry (申万行业字典表)

申万行业分类，支持三级层级结构。一级分类共 31 个行业。

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| industry_code | VARCHAR(10) PK | yes | 行业代码（如 110000） |
| name | VARCHAR(30) | yes | 行业名称（如 农林牧渔） |
| level | TINYINT | yes | 层级：1=一级, 2=二级, 3=三级 |
| parent_code | VARCHAR(10) | no | 父级行业代码（一级为 NULL） |
| display_order | INT | yes | 显示顺序 |

**Indexes**: `idx_parent (parent_code)`

### 3. t_stock (股票基本信息表)

A 股股票主数据，跨模块共享。

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| stock_code | VARCHAR(10) PK | yes | 股票代码（如 600519） |
| name | VARCHAR(50) | yes | 股票简称（如 贵州茅台） |
| full_name | VARCHAR(100) | no | 股票全称 |
| exchange | ENUM('SH','SZ','BJ') | yes | 交易所 |
| list_date | DATE | no | 上市日期 |
| is_active | BOOLEAN | yes | 是否正常交易 |

### 4. t_stock_industry (股票-行业关联表)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | VARCHAR(32) PK | yes | 主键 UUID |
| stock_code | VARCHAR(10) | yes | 股票代码 |
| industry_code | VARCHAR(10) | yes | 行业代码 |
| is_primary | BOOLEAN | yes | 是否为主要所属行业 |
| classification_source | ENUM('official','ai_extracted','user_defined') | yes | 分类来源 |

**Unique**: `uk_stock_industry (stock_code, industry_code)`

### 5. t_analysis_article (AI 分析文章主表)

AI 生成的分析报告，知识库核心实体。

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| article_id | VARCHAR(32) PK | yes | 文章 UUID |
| title | VARCHAR(50) | yes | AI 生成标题（≤15字），用户可编辑 |
| summary | VARCHAR(200) | yes | AI 生成摘要（≤80字，2句话结论导向） |
| content | TEXT | yes | 分析正文（Markdown 格式） |
| event_type | ENUM('geopolitical','policy','earnings','supply_chain','other') | yes | 事件类型 |
| raw_input | VARCHAR(500) | yes | 用户原始输入（≥10字） |
| chain_table | JSON | no | 产业链传导表（仅 supply_chain 类型） |
| user_id | VARCHAR(32) | yes | 用户编号（FK → t_user） |

**Indexes**: `idx_user_id (user_id)`

> 注意：行业标签和提及股票通过独立关联表管理（见下方），不在此表存储 JSON。

### 6. t_article_industry (文章-行业关联表)

替代原先的 JSON `industry_tags` 字段，支持按行业精确查询和统计。

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | VARCHAR(32) PK | yes | 主键 UUID |
| article_id | VARCHAR(32) | yes | 文章 UUID |
| industry_code | VARCHAR(10) | yes | 行业代码（FK → t_industry） |
| chain_level | INT | no | 产业链传导层级（仅产业链分析） |

**Unique**: `uk_article_industry (article_id, industry_code)`
**Indexes**: `idx_article_id`, `idx_industry_code`

### 7. t_article_stock (文章-股票关联表)

替代原先的 JSON `mentioned_stocks` 字段，支持按股票精确查询（股票视图）。

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | VARCHAR(32) PK | yes | 主键 UUID |
| article_id | VARCHAR(32) | yes | 文章 UUID |
| stock_code | VARCHAR(10) | yes | 股票代码 |
| stock_name | VARCHAR(50) | yes | 股票名称（冗余快照） |

**Unique**: `uk_article_stock (article_id, stock_code)`
**Indexes**: `idx_article_id`, `idx_stock_code`

### 8. t_event_reminder (大事提醒表)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| reminder_id | VARCHAR(32) PK | yes | 提醒 UUID |
| title | VARCHAR(100) | yes | 事件名称 |
| event_date | DATE | yes | 事件日期 |
| industry_tags | JSON | no | 关联行业（冗余便于展示） |
| status | ENUM('pending','reminded_3day','reminded_today','archived') | yes | 提醒状态（4 阶段） |
| user_id | VARCHAR(32) | yes | 用户编号（FK → t_user） |

**Indexes**: `idx_user_id (user_id)`

> 状态流：`pending` → `reminded_3day`（提前3天）→ `reminded_today`（当天）→ `archived`（过期归档）

### 9. t_chat_session (对话会话表)

多轮对话上下文管理，支持用户与 AI 的持续交互。

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| session_id | VARCHAR(32) PK | yes | 会话 UUID |
| user_id | VARCHAR(32) | yes | 用户编号 |
| title | VARCHAR(100) | no | 会话标题（自动生成或用户编辑） |

**Indexes**: `idx_user_id (user_id)`

### 10. t_chat_message (对话消息表)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| message_id | VARCHAR(32) PK | yes | 消息 UUID |
| session_id | VARCHAR(32) | yes | 所属会话（FK → t_chat_session） |
| role | ENUM('user','assistant','system') | yes | 角色 |
| content | TEXT | yes | 消息内容 |

**Indexes**: `idx_session_id (session_id)`

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
PENDING = "pending"                # 待触发
REMINDED_3DAY = "reminded_3day"    # 已发3天前提醒
REMINDED_TODAY = "reminded_today"  # 已发当天提醒
ARCHIVED = "archived"              # 已归档（过期）
```

### ChainTableEntry (产业链传导表 JSON 结构)

```json
{
  "level": 1,
  "industry": "石油石化",
  "logic": "油价上涨直接推升成本",
  "direction": "受益",
  "degree": "高",
  "timing": "短期（1-4周）",
  "stocks": [{"code": "601857", "name": "中国石油"}]
}
```

## State Transitions

### Article Lifecycle

```
[用户输入] → [AI 分析中] → [结果展示] → [用户确认行业/股票标签] → [保存到知识库]
                                    ↓
                              [不保存/丢弃]
```

### Reminder Lifecycle

```
[创建提醒]
    → pending
    → reminded_3day（提前3天自动切换）
    → reminded_today（当天自动切换）
    → archived（过期后自动归档）
```

## 与原 data-model.md 的变更对照

| 项目 | 原方案 | 新方案 | 原因 |
|------|--------|--------|------|
| 行业标签 | JSON `industry_tags` | 独立关联表 `t_article_industry` | 支持精确查询和按行业统计 |
| 股票引用 | JSON `mentioned_stocks` | 独立关联表 `t_article_stock` | 支持股票视图精确匹配 |
| 行业数据 | 静态 JSON 文件 | 字典表 `t_industry` + `t_stock_industry` | 支持三级分类、跨模块共享 |
| 用户 | 预留 `user_id` 字段 | 独立用户表 `t_user` | 支持认证和多用户 |
| 股票 | 无主数据 | 独立股票表 `t_stock` | 跨模块共享，模块二/三复用 |
| 提醒状态 | 3 状态 | 4 状态（细化提醒阶段） | 更精确的提醒流程追踪 |
| 对话 | 无 | `t_chat_session` + `t_chat_message` | 支持多轮对话上下文 |
| 全局 | 无软删除/审计 | 所有表含 `deleted` + 审计字段 | 生产规范 |

## 完整 DDL

> 详见 `docs/FEATURES/AI_Analysis/ai-analysis.ddl.md`
