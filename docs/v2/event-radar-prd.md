# Product Requirements Document: 投资事件影响雷达

**Version**: 1.0
**Date**: 2026-05-11
**Author**: Sarah (Product Owner)
**Quality Score**: 92/100
**核心命题**: 系统比用户更早发现——哪些事件正在影响他的投资

---

## Executive Summary

散户每天面对数百条财经新闻，真正需要知道的只有 3-5 条，但他不知道是哪几条。现有 AI 股票分析平台的三模块（AI 分析 / 行情数据 / 数据工具）已具备强大的分析能力，但**起点都是用户主动触发**——用户不输入，系统就不会行动。

「投资事件影响雷达」是平台的第四模块，核心使命是**将系统的起点从"用户"变为"系统自身"**。系统持续监测财经信息源，自动识别影响用户自选股的事件，主动告知用户并一键联动现有分析能力。

与头部平台（新浪财经、同花顺、东方财富）的广播式新闻推送不同，本模块做的是**基于自选股 + 知识库的精准窄播**——只告诉用户"这件事正在影响你的投资"。同时，知识库历史分析的联动能力是头部平台无法复制的**独有壁垒**。

---

## Problem Statement

**Current Situation**: 模块一已具备强大的事件分析和个股分析能力，但完全依赖用户主动触发。用户必须自己先看到新闻 → 想起来去分析 → 手动输入。大量影响用户投资的事件在用户不知情的情况下发生了。

**Proposed Solution**: 构建「投资事件影响雷达」模块，系统自动采集信息 → 提取关联股票/行业 → 匹配用户自选股 → 判断影响方向和置信度 → 主动推送给用户，并提供一键深度分析入口。

**Business Impact**:
- 从"用户找事件"到"事件找用户"，彻底改变产品价值交付方式
- 直接拉动模块一（事件分析 / 个股分析）的使用频次
- 通过知识库联动形成正循环，系统越用越精准

---

## Success Metrics

**Primary KPIs:**

| 指标 | 目标 | 衡量方式 |
|------|------|----------|
| 影响匹配准确率 | ≥ 80% | 用户反馈"相关/不相关"的比例 |
| 日活面板打开率 | ≥ 60% | 每日打开影响雷达面板的用户占比 |
| 预警点击率 | ≥ 40% | 收到预警后点击查看详情的比例 |
| 一键分析转化率 | ≥ 15% | 从面板/预警跳转到模块一分析的比例 |
| 用户满意度 | ≥ 4.0/5 | 定期调研 |

**Validation**: 上线后 2 周内收集首批用户反馈，重点关注"准确率"和"转化率"两个指标。

---

## User Personas

### Primary: A 股个人投资者（散户）

- **Role**: 持有 ≤ 30 只自选股的个人投资者
- **Goals**: 快速了解影响自己投资的事件，不漏掉重要信息，不错过交易机会
- **Pain Points**:
  - 每天刷多个 App 看新闻，效率低，容易漏
  - 看到新闻不知道会不会影响自己持有的股票
  - 分析过的东西下次就忘了，无法形成知识积累
- **Technical Level**: 中等，能使用 Web 应用，不熟悉专业金融工具
- **使用场景**: 通勤时扫一眼晨报、上班间隙看一眼面板、收到预警后快速判断

---

## User Stories & Acceptance Criteria

### Story 1：查看影响雷达面板

**作为** A 股散户
**我希望** 打开「事件雷达」页面，立即看到此刻正在影响我投资的事件
**从而** 不需要刷新闻 App，系统替我盯着

**Acceptance Criteria:**
- [ ] 页面顶部显示"正在影响"区域，列出当前活跃的影响事件卡片
- [ ] 每张事件卡片包含：事件标题、来源、时间、影响到的自选股列表（股票名+代码+方向+置信度）
- [ ] 影响方向用颜色标注：利好绿色 ▲ / 利空红色 ▼ / 中性灰色 —
- [ ] 页面显示"上次扫描时间"，距当前 ≤ 15 分钟
- [ ] "今日已影响"区域展示当天已归档的影响事件列表，按时间倒序
- [ ] 影响概览区域展示统计数据：今日影响事件数、涉及自选股数、本周累计数
- [ ] 每张卡片底部有操作按钮：[查看原文] [AI解读] [一键分析]
- [ ] 无影响事件时显示空状态提示
- [ ] 页面加载时间 ≤ 2 秒

---

### Story 2：一键分析影响事件

**作为** A 股散户
**我希望** 在影响雷达面板中点击"一键分析"，直接进入事件深度分析
**从而** 快速理解这个事件对市场的具体影响，无需手动输入

**Acceptance Criteria:**
- [ ] 点击卡片上的"一键分析"按钮，跳转到模块一的事件分析页面
- [ ] 事件标题和摘要自动预填到分析输入框中
- [ ] 事件类型自动匹配（地缘政治 / 政策法规 / 财报季报 / 产业链分析 / 其他）
- [ ] 跳转后自动触发分析流程，无需用户再次确认
- [ ] 分析完成后结果保存到知识库，并在影响事件卡片上显示"已分析"标记

---

### Story 3：接收影响预警推送

**作为** A 股散户
**我希望** 当高优先级事件影响我的自选股时，系统主动推送通知
**从而** 即使不打开系统，也能第一时间知道

**Acceptance Criteria:**
- [ ] 页面右上角铃铛图标显示未读预警数量（红点数字）
- [ ] 点击铃铛弹出预警摘要 Drawer，展示最近预警列表
- [ ] 每条预警包含：事件标题、影响到的自选股、方向、置信度
- [ ] 预警按优先级排序：P0（紧急）> P1（重要）
- [ ] 预警卡片底部有"查看详情"和"一键分析"两个按钮
- [ ] 查看后预警标记为已读，红点数字更新
- [ ] 每日 P0+P1 预警 ≤ 5 条（超过的不推送，仅纳入面板）
- [ ] 预警触发条件：
  - P0：自选股直接出现在事件中心 + 置信度 > 80%
  - P1：自选股所属行业出现重大事件 + 置信度 > 70%
- [ ] 点击"查看详情"弹出事件详情 Drawer（不打断当前操作）
- [ ] 点击"一键分析"跳转模块一事件分析（预填内容）

---

### Story 4：查看影响晨报

**作为** A 股散户
**我希望** 每天早上打开系统时，看到个性化的投资影响晨报
**从而** 30 秒内了解"昨晚发生了什么，今天开盘要注意什么"

**Acceptance Criteria:**
- [ ] 每天 6:30 自动生成晨报（LangGraph 工作流）
- [ ] 用户当日首次登录时，弹出晨报全屏展示
- [ ] 晨报包含以下板块：
  - AI 一句话总结（整体判断利好/利空/中性）
  - 影响你的事件列表（与 Story 1 卡片格式一致）
  - 自选股影响概览（每只受影响的自选股 + 昨收价 + 影响方向 + 相关新闻数）
  - 今日关注（可能影响市场的预排事件）
- [ ] 晨报 100% 个性化：只展示与用户自选股/关注行业相关的内容
- [ ] 底部有"开始今日分析"和"查看影响雷达"两个入口
- [ ] 用户可关闭晨报，进入正常工作界面
- [ ] 晨报可回溯查看历史版本（最近 7 天）
- [ ] 晨报生成时间 ≤ 30 秒

---

### Story 5：事件详情与 AI 解读

**作为** A 股散户
**我希望** 点击影响事件后看到完整的 AI 解读
**从而** 不仅知道"发生了什么"，还理解"为什么影响我的投资"

**Acceptance Criteria:**
- [ ] 点击事件的"查看详情"或"AI解读"，弹出事件详情 Drawer
- [ ] Drawer 包含三段式布局：
  - 上部：原文摘要（标题 + 来源 + 时间 + 正文摘要 ≤ 200 字）+ [查看原文] 链接
  - 中部：AI 影响解读（事件性质 / 影响行业 / 对每只自选股的影响原因）
  - 下部：行动按钮区（一键分析事件 / 查看K线 / 个股深度分析 / 查看历史分析）
- [ ] AI 解读中每只自选股的影响原因用自然语言说明（不只标注利好/利空，还说为什么）
- [ ] 如果知识库中有相关历史分析，在"知识库关联"区域展示（标题 + 分析日期 + 结论摘要）
- [ ] 点击"查看K线"弹出全局股票抽屉
- [ ] 点击"个股深度分析"跳转模块一个股分析页面
- [ ] 点击"查看历史分析"跳转知识库对应文章
- [ ] AI 解读生成方式：基于事件内容 + 影响判断结果，调用 LLM 生成（非实时流式，预生成缓存）

---

### Story 6：自选股页面增强影响徽标

**作为** A 股散户
**我希望** 在自选股列表页面看到每只股票的影响状态
**从而** 在同一个页面内同时了解"行情 + 什么在影响行情"

**Acceptance Criteria:**
- [ ] 自选股表格每行新增"影响"列，位于涨跌幅列之后
- [ ] 影响列展示：最近 24 小时相关影响事件数量 + 方向颜色点（绿色偏利好 / 红色偏利空 / 灰色无影响）
- [ ] 点击影响列，展开该股最近 5 条影响事件的摘要列表（Popover 或 Drawer）
- [ ] 摘要列表中每条包含：事件标题（可点击跳转详情）、影响方向、置信度
- [ ] 不改变现有自选股页面的整体布局，只增加一列

---

### Story 7：影响范围配置

**作为** A 股散户
**我希望** 自定义系统的监测范围和预警灵敏度
**从而** 让系统的判断更贴合我的需求

**Acceptance Criteria:**
- [ ] 事件雷达页面提供"设置"入口
- [ ] 可配置项：
  - 关注的行业（从申万 31 个一级行业中多选）
  - 关注的事件类型（政策法规 / 公司公告 / 行业动态 / 宏观经济 / 地缘政治）
  - 预警灵敏度（高：所有相关事件都推 / 中：只推高置信度 / 低：只推直接影响）
  - 免打扰时段（如 22:00 - 7:00 不推送预警）
- [ ] 关注的股票默认取自自选股，无需额外配置
- [ ] 保存后即时生效
- [ ] 默认配置即可满足 80% 用户需求（关注行业自动从自选股推断，灵敏度默认"中"）

---

## Functional Requirements

### Core Feature 1: 事件采集与影响判断管线

**Description**: 系统后台持续运行的信息采集、事件提取和影响判断引擎。

**User Flow**: 无用户交互，系统后台自动运行。

**Processing Pipeline**:
```
信息源采集 → 去重聚合 → 关联提取 → 用户匹配 → 影响判断 → 优先级计算 → 入库 + 触发推送
```

**Step 1 - 信息源采集**:
- 专用信息源（财联社快讯 API/RSS）：每 10 分钟采集一次（交易时段）/ 每 1 小时（非交易时段）
- 现有搜索引擎（Tavily / Anspire / Bocha）：按自选股相关关键词定时搜索，补充覆盖
- 采集结果以 RawEventItem 格式入库待处理

**Step 2 - 去重聚合**:
- URL MD5 hash 精确去重
- 标题 TF-IDF 余弦相似度语义去重（阈值 0.7）
- 相似新闻归并为同一事件，source_count 累加

**Step 3 - 关联提取**（复用 MetadataExtractor）:
- 正则匹配股票代码和标准格式
- 名称匹配（查 t_stock 表）
- 行业关键词匹配（查行业-关键词映射表）
- LLM 兜底（对规则引擎低置信度的）

**Step 4 - 用户匹配**:
- 事件关联的股票与每个用户的自选股取交集
- 事件关联的行业与用户的关注行业取交集
- 生成 per-user 的影响关联记录

**Step 5 - 影响判断**:
- 规则引擎（快速路径）：利好/利空词汇库关键词匹配 → sentiment + confidence
- LLM 兜底（对规则引擎 confidence < 0.6 的）：调用 LLM 判断影响方向和原因

**Step 6 - 优先级计算**:
- P0（紧急）：直接涉及自选股 + confidence > 0.8 + importance = high
- P1（重要）：涉及关注行业 + confidence > 0.7
- P2（关注）：其他相关事件

**Edge Cases**:
- 信息源采集失败：记录失败日志，不影响下一轮采集；不阻塞处理管线
- 去重误判（不同事件被合并）：人工可拆分（Phase 2）
- 关联提取无结果：标记为"未分类"，不入影响面板
- 所有用户都不相关的事件：正常入库但不生成 user_impact 记录
- 自选股为空的用户：不生成任何影响记录，显示引导"添加自选股以启用影响监测"

---

### Core Feature 2: 影响雷达面板（前端）

**Description**: 用户查看当前影响事件的核心交互页面。

**Page Route**: `/event-radar`

**Layout**:
- 顶部：页面标题"投资事件影响雷达" + 上次扫描时间 + 设置按钮
- 主体上半部分（正在影响）：活跃影响事件卡片列表
- 主体下半部分（今日已影响）：已归档影响事件折叠列表
- 底部：影响概览统计

**Interaction**:
- 页面打开时调用 API 获取当前用户的影响事件列表
- 交易时段内每 60 秒自动刷新（轮询）
- 非交易时段不自动刷新
- 卡片点击"查看详情"→ 弹出事件详情 Drawer
- 卡片点击"一键分析"→ 跳转 `/analysis` 并预填事件内容
- 卡片点击"查看原文"→ 新窗口打开原始报道 URL

**States**:
- Loading：骨架屏
- Empty（无影响事件）："暂无影响你投资的事件，系统正在持续监测中"
- Error："加载失败，请稍后重试"

---

### Core Feature 3: 预警推送系统

**Description**: P0/P1 级别事件的主动推送机制。

**Trigger**: 影响判断管线输出 P0 或 P1 级别事件时触发。

**Processing**:
1. 检查用户免打扰时段设置
2. 检查当日已推送数量（≤ 5 条限制）
3. 生成预警消息，写入 `t_user_alert`
4. 前端轮询获取未读预警（60 秒间隔），更新铃铛数字

**Alert Drawer**:
- 右侧弹出，不打断当前操作
- 展示预警摘要列表（按优先级排序）
- 每条预警可点击展开详情或跳转分析

**Edge Cases**:
- 免打扰时段内的 P0 预警：延后到免打扰结束后推送
- 当日预警已达 5 条上限：后续 P0/P1 仅入库，不推送
- 用户未登录：预警入库，下次登录时在铃铛中展示

---

### Core Feature 4: 影响晨报生成

**Description**: LangGraph 驱动的每日个性化晨报自动生成。

**Trigger**: APScheduler 每天 6:30 触发。

**LangGraph Workflow**:
```
START
  → collect_impact_events (收集过去24小时该用户的影响事件)
  → collect_portfolio_status (获取自选股昨日收盘行情)
  → match_knowledge_context (匹配知识库历史分析)
  → generate_briefing (LLM 生成晨报：AI一句话 + 事件列表 + 自选股概览 + 今日关注)
  → save_briefing (持久化到 t_morning_briefing)
  → END
```

**Output Format**: 结构化 JSON（AI一句话 + 影响事件列表 + 自选股概览 + 今日关注事项），前端渲染为卡片式布局。

**Edge Cases**:
- 过去24小时无影响事件：生成"平静日"晨报，提示"昨晚到今晨无重大事件影响你的投资"
- 自选股为空：不生成晨报，引导用户添加自选股
- LLM 生成失败：使用模板兜底（事件列表拼接，无 AI 总结）

---

### Core Feature 5: 用户投资画像

**Description**: 为每个用户维护投资画像，支撑精准影响匹配。

**画像数据来源**:
- 自选股列表：`t_watchlist_item`（实时读取，不缓存）
- 关注行业：从自选股行业 + 用户配置中获取
- 分析历史：`t_analysis_article` + `t_article_stock` + `t_article_industry`（用于知识库联动）
- 分析信号：`t_stock_analysis` 中的信号提取结果

**画像更新时机**:
- 自选股变更时实时更新
- 分析历史每次分析完成后更新
- 行业配置变更时更新

---

### Out of Scope (本期不做)

| 功能 | 说明 |
|------|------|
| 浏览器通知推送 (Web Notification API) | Phase 2 实现，MVP 只做页面内通知 |
| 财联社/东财/巨潮以外的信息源 | MVP 做一个专用信息源 + 3 个搜索引擎 |
| 事件详情页（独立完整页面） | MVP 用 Drawer 展示，Phase 2 考虑独立页面 |
| 周度影响回顾报告 | Phase 2 |
| 用户反馈"不相关"的闭环优化 | Phase 2 |
| AI 完整解读的实时流式生成 | MVP 预生成缓存，Phase 2 支持实时流式 |
| 多用户预警频率 A/B 测试 | Phase 2 |

---

## Technical Constraints

### Performance

| 指标 | 目标 | 说明 |
|------|------|------|
| 影响雷达面板加载 | ≤ 2 秒 | 从本地数据库查询 |
| 影响事件扫描到面板可见延迟 | ≤ 15 分钟 | 交易时段每 10 分钟扫描 |
| 预警从产生到推送延迟 | ≤ 5 分钟 | 影响判断完成后立即触发 |
| 晨报生成时间 | ≤ 30 秒 | LangGraph 工作流，从本地数据聚合 |
| 面板自动刷新 | 60 秒间隔 | 交易时段内前端轮询 |
| 单次信息采集处理时间 | ≤ 60 秒 | 包括采集 + 去重 + 影响判断全流程 |

### Security & Compliance

- **版权合规**：只展示标题 + 摘要（≤ 200 字），原文链接跳转外部网站；AI 解读为系统原创内容
- **数据隔离**：每个用户的影响事件独立计算（`t_user_impact` 包含 `user_id`），API 层面自动注入用户身份
- **不构成投资建议**：页面底部或影响卡片上须展示"以上为 AI 分析参考，不构成投资建议"声明

### Integration Requirements

| 对接系统 | 集成方式 | 说明 |
|----------|----------|------|
| 模块一事件分析（系统A） | 路由跳转 + URL 参数 | "一键分析"跳转 `/analysis` 并预填事件内容 |
| 模块一个股分析（系统B） | 路由跳转 | "个股深度分析"跳转 `/stock-analysis` |
| 模块二全局股票抽屉 | Zustand Store | 调用 `stockDrawerStore.open(code)` |
| 模块二自选股数据 | API 调用 | 读取 `t_watchlist_item` 获取用户自选股 |
| 模块一知识库 | API 调用 + DB 查询 | 读取 `t_analysis_article` 匹配历史分析 |
| MetadataExtractor | 直接复用 Domain 层 | 调用现有股票/行业提取逻辑 |
| SearchService | 直接复用 Infrastructure 层 | 调用 Tavily/Anspire/Bocha 搜索引擎 |
| APScheduler | 已引入 | 定时任务调度 |
| LangGraph | 已引入 | 晨报生成工作流 |

### Technology Stack

- **后端**: Python FastAPI + SQLAlchemy 2.0 (async) + APScheduler + LangGraph
- **前端**: React 18 + TypeScript + Ant Design 5 + Zustand
- **信息采集**: 财联社 API/RSS（专用源） + BeautifulSoup + 现有 SearchService
- **影响判断**: 规则引擎（关键词匹配） + LLM 兜底（复用 AIService）
- **数据存储**: MySQL（新增 4 张表） + Redis（缓存）

---

## Data Model

### 新增数据库表

**t_impact_event (影响事件)**
```sql
CREATE TABLE t_impact_event (
  event_id          BIGINT AUTO_INCREMENT PRIMARY KEY,
  title             VARCHAR(200) NOT NULL COMMENT '事件标题',
  summary           VARCHAR(500) COMMENT 'AI生成摘要',
  event_type        VARCHAR(20) COMMENT 'geopolitical/policy/earnings/industry/macro/other',
  sentiment         VARCHAR(10) COMMENT 'positive/negative/neutral',
  importance        VARCHAR(10) COMMENT 'high/medium/low',
  affected_industries JSON COMMENT '[{name, direction}]',
  affected_stocks   JSON COMMENT '[{code, name, direction, confidence, reason}]',
  source_count      INT DEFAULT 1 COMMENT '来源数量',
  first_seen_at     DATETIME NOT NULL COMMENT '首次发现时间',
  last_seen_at      DATETIME NOT NULL COMMENT '最后更新时间',
  is_active         TINYINT DEFAULT 1 COMMENT '是否仍在活跃影响中',
  created_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_first_seen (first_seen_at),
  INDEX idx_event_type (event_type),
  INDEX idx_is_active (is_active)
) COMMENT='影响事件主表';
```

**t_impact_article (事件原始报道)**
```sql
CREATE TABLE t_impact_article (
  article_id    BIGINT AUTO_INCREMENT PRIMARY KEY,
  event_id      BIGINT NOT NULL COMMENT '关联事件',
  title         VARCHAR(200) NOT NULL,
  content       VARCHAR(500) COMMENT '摘要，≤500字',
  source        VARCHAR(50) NOT NULL COMMENT '来源网站（cls/sina/eastmoney/tavily等）',
  url           VARCHAR(500) NOT NULL,
  url_hash      VARCHAR(32) NOT NULL COMMENT 'URL MD5，去重用',
  published_at  DATETIME COMMENT '原文发布时间',
  crawled_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE INDEX idx_url_hash (url_hash),
  INDEX idx_event_id (event_id),
  FOREIGN KEY (event_id) REFERENCES t_impact_event(event_id)
) COMMENT='事件原始报道';
```

**t_user_impact (用户-事件影响关联)**
```sql
CREATE TABLE t_user_impact (
  id              BIGINT AUTO_INCREMENT PRIMARY KEY,
  user_id         BIGINT NOT NULL COMMENT '用户ID',
  event_id        BIGINT NOT NULL COMMENT '事件ID',
  matched_stocks  JSON COMMENT '[{code, name, direction, confidence}] 匹配到的自选股',
  matched_industries JSON COMMENT '[{name, direction}] 匹配到的关注行业',
  priority        VARCHAR(5) NOT NULL COMMENT 'P0/P1/P2',
  is_read         TINYINT DEFAULT 0 COMMENT '是否已读',
  is_alert_sent   TINYINT DEFAULT 0 COMMENT '是否已推送预警',
  created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_user_priority (user_id, priority),
  INDEX idx_user_read (user_id, is_read),
  INDEX idx_event_id (event_id),
  FOREIGN KEY (event_id) REFERENCES t_impact_event(event_id)
) COMMENT='用户-事件影响关联（每用户独立）';
```

**t_morning_briefing (影响晨报)**
```sql
CREATE TABLE t_morning_briefing (
  id              BIGINT AUTO_INCREMENT PRIMARY KEY,
  user_id         BIGINT NOT NULL COMMENT '用户ID',
  briefing_date   DATE NOT NULL COMMENT '晨报日期',
  ai_summary      VARCHAR(200) COMMENT 'AI一句话总结',
  content         JSON NOT NULL COMMENT '晨报结构化内容',
  is_read         TINYINT DEFAULT 0 COMMENT '是否已读',
  created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE INDEX idx_user_date (user_id, briefing_date),
  FOREIGN KEY (user_id) REFERENCES t_user(id)
) COMMENT='每日影响晨报';
```

**t_user_alert (预警记录)**
```sql
CREATE TABLE t_user_alert (
  id              BIGINT AUTO_INCREMENT PRIMARY KEY,
  user_id         BIGINT NOT NULL,
  user_impact_id  BIGINT NOT NULL COMMENT '关联的用户影响记录',
  priority        VARCHAR(5) NOT NULL COMMENT 'P0/P1',
  title           VARCHAR(200) NOT NULL COMMENT '预警标题',
  summary         VARCHAR(500) COMMENT '预警摘要',
  is_read         TINYINT DEFAULT 0,
  created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_user_read (user_id, is_read),
  INDEX idx_created (created_at),
  FOREIGN KEY (user_impact_id) REFERENCES t_user_impact(id)
) COMMENT='预警推送记录';
```

**t_radar_config (用户雷达配置)**
```sql
CREATE TABLE t_radar_config (
  id              BIGINT AUTO_INCREMENT PRIMARY KEY,
  user_id         BIGINT NOT NULL UNIQUE,
  focused_industries JSON COMMENT '关注行业列表',
  event_types     JSON COMMENT '关注事件类型',
  alert_sensitivity VARCHAR(10) DEFAULT 'medium' COMMENT 'high/medium/low',
  quiet_hours_start TIME COMMENT '免打扰开始时间',
  quiet_hours_end   TIME COMMENT '免打扰结束时间',
  updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES t_user(id)
) COMMENT='用户雷达配置';
```

### 与现有表的关系

| 新表 | 关联现有表 | 关系 |
|------|-----------|------|
| t_user_impact.user_id | t_user | 用户数据隔离 |
| t_user_impact.matched_stocks | t_watchlist_item | 自选股匹配 |
| t_user_alert.user_impact_id | t_user_impact | 预警关联影响 |
| t_radar_config.user_id | t_user | 配置归属 |
| t_morning_briefing.user_id | t_user | 晨报归属 |

---

## API Endpoints

### 影响雷达面板

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/event-radar/impacts` | 获取当前用户的影响事件列表（active + today） |
| GET | `/api/v1/event-radar/impacts/{id}` | 获取影响事件详情 |
| GET | `/api/v1/event-radar/stats` | 获取影响概览统计 |
| POST | `/api/v1/event-radar/impacts/{id}/ai-insight` | 生成/获取 AI 解读 |

### 预警推送

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/event-radar/alerts` | 获取未读预警列表 |
| GET | `/api/v1/event-radar/alerts/unread-count` | 获取未读预警数量 |
| PUT | `/api/v1/event-radar/alerts/{id}/read` | 标记预警已读 |

### 影响晨报

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/event-radar/briefing/today` | 获取今日晨报 |
| GET | `/api/v1/event-radar/briefing/history` | 获取历史晨报列表（最近7天） |
| PUT | `/api/v1/event-radar/briefing/{id}/read` | 标记晨报已读 |

### 配置

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/event-radar/config` | 获取用户雷达配置 |
| PUT | `/api/v1/event-radar/config` | 更新用户雷达配置 |

### 自选股影响增强

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/event-radar/stock-impacts` | 批量获取自选股影响状态（为自选股页面徽标提供数据） |

---

## MVP Scope & Phasing

### Phase 0: 基础设施（1 周）

- E-1: 事件采集管线框架（APScheduler 定时任务 + 管线骨架）
- E-2: 去重与聚合引擎（URL hash + 标题相似度）
- E-3: 用户投资画像构建（自选股 + 关注行业读取）
- E-5: 统一信息源抽象层 + 财联社 Provider 实现
- 数据库表创建（6 张新表）

### Phase 1: 核心价值 MVP（2-3 周）

- **投资影响雷达面板**（Story 1 + Story 5）：
  - 后端：信息采集 + 去重 + 关联提取 + 影响判断 + 用户匹配
  - 前端：面板页面 + 事件详情 Drawer
- **一键分析联动**（Story 2）：跳转模块一并预填
- **自选股影响徽标**（Story 6）：增强现有自选股页面

### Phase 2: 推模式（1-2 周）

- **影响预警推送**（Story 3）：P0/P1 判断 + 铃铛通知 + 预警 Drawer
- **影响晨报**（Story 4）：LangGraph 工作流 + 晨报展示页面

### Phase 3: 精细化（持续）

- **影响范围配置**（Story 7）：用户自定义监测范围
- 新增信息源（东财 / 巨潮资讯）
- 浏览器通知（Web Notification API）
- 用户反馈"不相关"的优化闭环
- 事件详情独立页面
- 周度影响回顾

---

## Page Navigation Update

```
侧边栏菜单（新增「事件雷达」后）：
├── 事件雷达          → /event-radar        （NEW！投资影响雷达面板）
├── 事件分析          → /analysis            （ChatGPT 对话式事件分析）
├── 个股分析          → /stock-analysis      （多Agent深度/快速分析）
│   └── 分析记录      → /analysis-records    （历史分析记录列表）
├── 知识库            → /knowledge           （三视图浏览+搜索）
├── 数据与工具
│   └── 数据同步      → /sync                （数据源管理+同步面板）
└── 行情数据
    ├── 自选股        → /market/watchlist     （分组管理+行情刷新+影响徽标）
    ├── 行业对比      → /market/industry      （申万31行业股票对比）
    └── 策略监控      → （即将推出）
```

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation Strategy |
|------|------------|--------|---------------------|
| 影响判断不准，推送无关事件 | High | High | MVP 先用规则引擎，精准优先于召回；每日预警 ≤ 5 条限制减少噪音；后续根据用户反馈优化 |
| 信息源反爬（财联社 IP 封禁） | High | Medium | 控制采集频率 ≥ 10 分钟；优先用 RSS/API 而非 HTML 爬取；备用搜索引擎兜底 |
| 版权合规（展示原文） | Medium | High | 只展示标题 + 摘要 ≤ 200 字，点击跳转原文链接；AI 解读为系统原创 |
| 用户觉得"和新闻 App 没区别" | Medium | High | UI 设计核心差异化："影响你的：xxx"始终在第一行；不展示不相关的事件 |
| 信息延迟（事件→用户 > 30 分钟） | Medium | Medium | 交易时段 10 分钟采集周期；P0 事件可触发即时采集（Phase 2） |
| 多用户影响计算性能（N 用户 × M 事件） | Low | Medium | 用户量小（≤ 100 用户），计算量可控；批量处理而非逐条 |
| LLM 兜底影响判断调用成本 | Low | Low | 仅对规则引擎低置信度（< 0.6）的调用 LLM，比例预估 < 20% |

---

## Appendix

### Glossary

- **影响事件 (Impact Event)**: 经系统采集、去重、关联提取后，可能影响用户投资的事件
- **影响判断 (Impact Assessment)**: 系统判断事件对用户自选股影响方向（利好/利空/中性）和置信度的过程
- **用户影响关联 (User Impact)**: 事件与特定用户的关联记录，包含匹配到的自选股和影响方向
- **P0/P1/P2**: 影响事件优先级，P0 最紧急（直接涉及自选股+高置信度），P2 最普通
- **影响雷达面板**: 用户查看当前影响事件的核心页面
- **影响晨报**: 每日个性化生成的投资影响摘要
- **MetadataExtractor**: 现有模块一的元数据提取器，可从文本中提取股票代码/名称和行业
- **知识库联动**: 影响事件与用户历史分析文章的关联匹配

### References

- 头脑风暴文档：`docs/v2/brainstorm-news-monitor.md`
- 产品概览 v2：`docs/v2/product-overview-v2.md`
- 模块一 PRD v2：`docs/v2/ai-analysis-prd-v2.md`
- 模块二 PRD v2：`docs/v2/market-data-prd-v2.md`
- 后端架构规范：`rules/backend.md`
- 前端架构规范：`rules/frontend.md`
- UI 设计规范：`DESIGN.md`

---

*This PRD was created through interactive requirements gathering with quality scoring to ensure comprehensive coverage of business, functional, UX, and technical dimensions.*
