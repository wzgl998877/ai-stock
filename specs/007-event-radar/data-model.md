# Data Model: 投资事件影响雷达

**Branch**: `007-event-radar` | **Date**: 2026-05-11

## 实体定义

### 1. ImpactEvent（影响事件）

系统从信息源采集并处理后的事件实体。全局共享，不按用户区分。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| event_id | BIGINT | PK, AUTO_INCREMENT | 事件 ID |
| title | VARCHAR(200) | NOT NULL | 事件标题 |
| summary | VARCHAR(500) | NULL | AI 生成摘要 |
| event_type | VARCHAR(20) | NULL | geopolitical/policy/earnings/industry/macro/other |
| sentiment | VARCHAR(10) | NULL | positive/negative/neutral |
| importance | VARCHAR(10) | NULL | high/medium/low |
| affected_industries | JSON | NULL | 关联行业列表 [{name, direction}] |
| affected_stocks | JSON | NULL | 关联股票列表 [{code, name, direction, confidence, reason}] |
| source_count | INT | DEFAULT 1 | 来源数量（≥3 标记为热点） |
| first_seen_at | DATETIME | NOT NULL | 首次发现时间 |
| last_seen_at | DATETIME | NOT NULL | 最后更新时间 |
| is_active | TINYINT | DEFAULT 1 | 是否仍在活跃影响中 |
| created_at | DATETIME | DEFAULT NOW | 创建时间 |

**索引**: idx_first_seen(first_seen_at), idx_event_type(event_type), idx_is_active(is_active)

**状态转换**: is_active: 1(活跃) → 0(归档)。归档条件：事件超过 24 小时未被更新，或手动归档。

**Validation**:
- title 不能为空
- affected_stocks JSON 格式必须为 [{code: str, name: str, direction: "positive"|"negative"|"neutral", confidence: float, reason: str}]
- confidence 取值范围 [0.0, 1.0]

---

### 2. ImpactArticle（事件原始报道）

影响事件的原始信息来源，与 ImpactEvent 是多对一关系。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| article_id | BIGINT | PK, AUTO_INCREMENT | 报道 ID |
| event_id | BIGINT | FK → ImpactEvent, NOT NULL | 关联事件 |
| title | VARCHAR(200) | NOT NULL | 报道标题 |
| content | VARCHAR(500) | NULL | 摘要（≤500字） |
| source | VARCHAR(50) | NOT NULL | 来源网站（cls/tavily/anspire/bocha 等） |
| url | VARCHAR(500) | NOT NULL | 原始 URL |
| url_hash | VARCHAR(32) | UNIQUE, NOT NULL | URL MD5（去重用） |
| published_at | DATETIME | NULL | 原文发布时间 |
| crawled_at | DATETIME | DEFAULT NOW | 采集时间 |

**索引**: idx_url_hash UNIQUE(url_hash), idx_event_id(event_id)

**Validation**:
- url_hash 必须唯一（精确去重保障）
- source 必须是已知来源之一

---

### 3. UserImpact（用户影响关联）

影响事件与特定用户的匹配记录。每用户独立计算。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT | PK, AUTO_INCREMENT | 记录 ID |
| user_id | BIGINT | NOT NULL | 用户 ID |
| event_id | BIGINT | FK → ImpactEvent, NOT NULL | 事件 ID |
| matched_stocks | JSON | NULL | 匹配到的自选股 [{code, name, direction, confidence}] |
| matched_industries | JSON | NULL | 匹配到的关注行业 [{name, direction}] |
| priority | VARCHAR(5) | NOT NULL | P0/P1/P2 |
| is_read | TINYINT | DEFAULT 0 | 是否已读 |
| is_alert_sent | TINYINT | DEFAULT 0 | 是否已推送预警 |
| created_at | DATETIME | DEFAULT NOW | 创建时间 |

**索引**: idx_user_priority(user_id, priority), idx_user_read(user_id, is_read), idx_event_id(event_id)

**Validation**:
- priority 必须是 P0/P1/P2 之一
- 同一 (user_id, event_id) 组合应唯一
- matched_stocks 不能为空（无匹配则不生成此记录）

**状态转换**:
- is_read: 0(未读) → 1(已读)
- is_alert_sent: 0(未推送) → 1(已推送)

---

### 4. UserAlert（预警记录）

P0/P1 级别影响事件的推送记录。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT | PK, AUTO_INCREMENT | 预警 ID |
| user_id | BIGINT | NOT NULL | 用户 ID |
| user_impact_id | BIGINT | FK → UserImpact, NOT NULL | 关联用户影响记录 |
| priority | VARCHAR(5) | NOT NULL | P0/P1 |
| title | VARCHAR(200) | NOT NULL | 预警标题 |
| summary | VARCHAR(500) | NULL | 预警摘要 |
| is_read | TINYINT | DEFAULT 0 | 是否已读 |
| created_at | DATETIME | DEFAULT NOW | 创建时间 |

**索引**: idx_user_read(user_id, is_read), idx_created(created_at)

**Validation**:
- priority 只能是 P0 或 P1
- 每个用户每日预警数量 ≤ 5 条

---

### 5. MorningBriefing（影响晨报）

每日为每个用户生成的个性化晨报。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT | PK, AUTO_INCREMENT | 晨报 ID |
| user_id | BIGINT | NOT NULL | 用户 ID |
| briefing_date | DATE | NOT NULL | 晨报日期 |
| ai_summary | VARCHAR(200) | NULL | AI 一句话总结 |
| content | JSON | NOT NULL | 结构化内容 |
| is_read | TINYINT | DEFAULT 0 | 是否已读 |
| created_at | DATETIME | DEFAULT NOW | 创建时间 |

**索引**: UNIQUE idx_user_date(user_id, briefing_date)

**Validation**:
- content JSON 结构必须包含 impact_events、portfolio_overview、today_focus 三个板块
- 每用户每天只有一份晨报

---

### 6. RadarConfig（用户雷达配置）

用户的个性化监测配置。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT | PK, AUTO_INCREMENT | 配置 ID |
| user_id | BIGINT | UNIQUE, NOT NULL | 用户 ID |
| focused_industries | JSON | NULL | 关注行业列表 ["电力设备", "石油石化"] |
| event_types | JSON | NULL | 关注事件类型 ["policy", "earnings"] |
| alert_sensitivity | VARCHAR(10) | DEFAULT 'medium' | high/medium/low |
| quiet_hours_start | TIME | NULL | 免打扰开始时间 |
| quiet_hours_end | TIME | NULL | 免打扰结束时间 |
| updated_at | DATETIME | ON UPDATE NOW | 更新时间 |

**Validation**:
- alert_sensitivity 必须是 high/medium/low
- quiet_hours_start 和 quiet_hours_end 必须同时设置或同时为空
- focused_industries 中的行业名称必须属于申万 31 个一级行业

---

## 实体关系图

```
ImpactEvent 1───N ImpactArticle
     │
     │ 1
     │
     N
UserImpact ──── User
     │ 1
     │
     1
UserAlert ───── User

MorningBriefing ── User

RadarConfig ────── User
```

## 与现有实体的关系

| 新实体 | 现有实体 | 关系 | 说明 |
|--------|----------|------|------|
| UserImpact.user_id | t_user.id | N:1 | 用户数据隔离 |
| UserImpact.matched_stocks | t_watchlist_item | 引用 | 通过 stock_code 关联自选股 |
| ImpactEvent.affected_stocks | t_stock | 引用 | 通过 stock_code 关联股票基础信息 |
| ImpactEvent.affected_industries | t_industry | 引用 | 通过行业名称关联行业分类 |
| MorningBriefing.content | t_analysis_article | 引用 | content 中引用知识库文章 ID |
