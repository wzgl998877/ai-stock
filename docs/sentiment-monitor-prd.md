# Product Requirements Document: 舆情监测（模块四）

**版本**: 1.0
**日期**: 2026-05-11
**作者**: PM & AI 协作
**质量评分**: 92/100
**迭代说明**: 首版，基于现有三模块代码和架构，设计舆情监测能力

---

## 执行摘要

面向A股散户的定向舆情监测模块，解决用户"怕错过自选股和关注行业的重要消息"这个核心焦虑。

与同花顺/东财的新闻推送不同，本模块的差异化在于：**只围绕你的自选股和关注行业定向监测，AI自动做情感分析，与缠论信号、K线行情、知识库三重联动**。

**核心理念**：舆情监测 ≠ 自动抓取新闻。而是"为你的投资组合定制的舆情雷达"——定向搜索、智能过滤、联动展示。

**与现有模块的关系**：
```
模块一（AI事件分析）     ← 舆情新闻一键触发AI深度分析
模块二（行情数据展示）    ← K线图标注舆情事件、个股页新增舆情标签页
模块三（策略监控）        ← 缠论信号+舆情情感共振提醒
模块四（舆情监测）        → 贯穿三模块的舆情增强能力
```

---

## 问题陈述

### 用户痛点

1. **信息遗漏恐惧**：持有十几只股票，不可能每天挨个去搜新闻，万一哪只出了大事没看到就亏了
2. **信息过载矛盾**：同时订阅了财经App推送、公众号、雪球，90%是噪音，想看的反而被淹没
3. **消息面与技术面割裂**：看到K线异动不知道是不是消息驱动的，看到新闻又不知道对技术面有什么影响
4. **分析断层**：看到重要新闻后，需要手动复制到模块一做AI分析，操作链条太长

### 现有工具的痛点

- 同花顺/东财的新闻推送是全量的，不是围绕用户持仓定制
- 雪球讨论质量参差不齐，噪音太多
- 没有任何工具把舆情和技术信号（缠论）放在一起看
- 新闻与个人分析记录（知识库）完全割裂

### 解决方案

- 基于用户自选股和关注行业，**定时定向搜索**相关舆情（复用已有 Tavily/Bocha/Anspire 三源搜索能力）
- AI自动做**情感分析**（正面/中性/负面），过滤噪音，只呈现值得关注的
- 舆情信息嵌入**K线图、自选股列表、知识库**等已有页面，不做独立页面
- 舆情新闻支持**一键触发模块一AI深度分析**，打通消息面→分析面闭环

---

## 成功指标

| 指标 | 目标 |
|------|------|
| 舆情搜索完成时间 | 全部自选股搜索完成 ≤ 60秒（50只以内） |
| 情感分析准确率 | 与人工标注一致率 ≥ 75%（MVP阶段目标） |
| 舆情数据时效性 | 交易时段每4小时更新一次，非交易时段每日更新一次 |
| 用户主动使用率 | 上线后2周内，自选股舆情卡片点击率 ≥ 30% |
| 一键分析转化率 | 从舆情新闻触发AI分析的比例 ≥ 10% |

---

## 用户画像

与现有产品一致：A股混合型散户，4-10只持仓，每天1-2小时，PC为主。

**新增场景**：
- 早盘前（8:30-9:25）：快速浏览自选股有无重大舆情
- 盘中：K线异动时，想快速确认是不是消息驱动的
- 收盘后：回顾今日舆情事件，判断是否需要更新分析

---

## 用户故事 & 验收标准

### Story 1：自选股舆情热度概览

**作为** 持有十几只自选股的散户
**我希望** 打开自选股列表时一眼看到哪些股票今天有重大舆情
**从而** 快速聚焦"有事发生"的股票，不用逐一去搜新闻

**验收标准：**
- [ ] 自选股列表（`WatchlistPage`）每行新增"舆情"列，位于"操作"列之前
- [ ] 舆情列显示舆情热度标签，三种状态：
  - 🔴 **热点**：该股今日有 ≥2 条相关新闻且综合情感偏正面/负面（非中性）—— 红色标签
  - 🟡 **关注**：该股今日有 1 条相关新闻 —— 黄色标签
  - ⚪ **平静**：该股近3日无相关新闻 —— 灰色标签（默认状态）
- [ ] 鼠标悬停热度标签时，显示 Tooltip 展示最近3条新闻标题（截断30字）+ 情感方向（正面🟢/中性⚪/负面🔴）
- [ ] 列表顶部新增筛选按钮"有舆情"，点击后仅显示"热点"和"关注"状态的股票
- [ ] 舆情数据在交易时段每4小时自动刷新一次（9:30 / 13:00 / 收盘后），非交易时段每日一次；页面右上角显示"舆情更新于 HH:mm"
- [ ] 自选股列表首次加载时，舆情数据与行情数据并行请求，不阻塞行情展示
- [ ] 舆情数据不可用（搜索服务未配置）时，舆情列显示"-"且无 Tooltip

---

### Story 2：个股舆情时间线

**作为** 正在研究某只股票的散户
**我希望** 在个股详情页看到该股近期所有相关舆情的时间线
**从而** 判断近期消息面的整体氛围是正面还是负面

**验收标准：**
- [ ] 个股详情页（`StockDetailPage`）底部标签页新增"舆情动态"标签，位于"相关分析"之后
- [ ] 标签名旁显示近7日舆情数量徽标，如"舆情动态 (5)"；为0时不显示数字
- [ ] "舆情动态"标签页分为上下两部分：
  - **上半部分（30%高度）**：情感趋势折线图（最近7天）
    - X轴：日期（最近7天）
    - Y轴：情感综合得分（-1 到 +1，负面到正面）
    - 每天一个数据点，悬停显示"日期 + 情感得分 + 新闻条数"
    - 中线 0 为虚线参考线，上方为正面，下方为负面
  - **下半部分（70%高度）**：新闻列表
    - 每条新闻显示：情感标签（正面🟢/中性⚪/负面🔴）+ 标题 + 来源 + 发布时间
    - 标题可点击，浏览器新标签页打开原文链接
    - 每条新闻右侧有"AI分析"按钮（见 Story 3）
    - 列表按发布时间倒序，最多展示最近20条，支持分页（每页10条）
- [ ] 无舆情数据时显示"暂无相关舆情"
- [ ] 情感趋势图使用 ECharts 渲染，风格与 K 线图统一（白色背景、主色 #533afd）

---

### Story 3：舆情新闻一键触发AI分析

**作为** 看到一条重要新闻的散户
**我希望** 点击"AI分析"按钮后直接生成对该事件影响A股的深度分析
**从而** 不用手工复制新闻内容再手动输入

**验收标准：**
- [ ] 舆情新闻列表每条新闻右侧有"AI分析"按钮（紫色文字链接）
- [ ] 点击后自动跳转至 `/analysis` 页面（模块一），同时：
  - 自动将新闻标题+摘要填入分析输入框
  - 根据新闻内容自动匹配事件类型（地缘政治/政策法规/财报季报/产业链/其他）
  - 自动触发分析（等同于用户点击"分析"按钮）
- [ ] 如果用户在模块一已有正在进行的分析，先弹窗确认"当前有分析进行中，是否中断并开始新分析？"
- [ ] AI分析完成后，保存文章时自动关联该新闻提及的股票代码和行业
- [ ] 在模块一分析历史中，通过舆情触发分析的文章标注"来自舆情"标签

---

### Story 4：K线图舆情事件标注

**作为** 正在看K线的散户
**我希望** 在K线图上看到重大舆情事件发生的位置
**从而** 直观判断"这根大阳线是不是消息驱动的"

**验收标准：**
- [ ] K线图（`KLineChart` 组件）在日K/周K模式下，于K线下方标注舆情事件气泡
- [ ] 气泡样式：小圆点（直径 6px），颜色根据情感方向区分——正面绿色、负面红色、中性灰色
- [ ] 仅标注"热点"级别舆情（情感得分绝对值 ≥ 0.5 的重要事件），避免气泡过多影响可读性
- [ ] 鼠标悬停气泡时显示 Tooltip："事件标题（截断20字）· 情感方向 · 发布日期"
- [ ] 气泡标注默认开启，K线图指标栏新增"舆情 开/关"开关控制显示
- [ ] 分时模式下不显示舆情气泡
- [ ] 舆情气泡通过 ECharts `markPoint` 实现，与缠论信号箭头共存不冲突

---

### Story 5：舆情驱动的每日早报

**作为** 每天早上需要快速了解全局的散户
**我希望** 每天开盘前自动生成一份围绕我自选股和关注行业的舆情摘要
**从而** 5分钟内掌握所有重要动态，不错过任何关键信息

**验收标准：**
- [ ] 每个交易日 8:00 自动生成舆情早报（通过 APScheduler 定时任务）
- [ ] 早报内容包含：
  - **自选股舆情摘要**：按舆情热度排序，每只股票一句话总结今日舆情方向
  - **关注行业动态**：用户知识库中保存过的行业，今日有重大新闻的行业列表
  - **重大事件提醒**：情感得分绝对值 ≥ 0.7 的重大事件，突出显示
- [ ] 早报通过站内通知推送（右上角铃铛图标显示红点数字 + "舆情早报"标题）
- [ ] 点击通知可直接展开早报内容（Modal 或跳转到首页早报区域）
- [ ] 早报中每条舆情均可点击"查看详情"跳转到个股舆情标签页，或点击"AI分析"触发深度分析
- [ ] 非交易日不生成早报（通过交易日历判断）
- [ ] 早报生成后缓存至 Redis，当日有效；用户多次查看不重复生成

---

### Story 6：舆情+缠论信号共振提醒

**作为** 同时关注技术面和消息面的散户
**我希望** 当缠论买点出现且同时舆情正面时收到特殊提醒
**从而** 获得更高可信度的交易参考信号

**验收标准：**
- [ ] 在模块三缠论信号计算完成后，同步检查该股近3日舆情情感综合得分
- [ ] 共振条件定义：
  - **强关注**：缠论买点 + 近3日舆情情感得分 ≥ 0.3（正面偏强）
  - **风险警示**：缠论卖点 + 近3日舆情情感得分 ≤ -0.3（负面偏强）
- [ ] 满足共振条件时，自选股列表的信号灯升级显示：
  - "强关注"：绿灯变为闪烁的绿色 ★ 图标 + "强关注"文字
  - "风险警示"：红灯变为闪烁的红色 ⚠ 图标 + "风险警示"文字
- [ ] 同时触发站内通知："【强关注】XXX 出现买点信号且近期舆情正面"
- [ ] 点击通知跳转到个股K线页，同时展示缠论箭头标注和舆情气泡
- [ ] 模块三未接入或模块三信号为"neutral"时，不触发共振判断
- [ ] 舆情数据不可用时，共振判断自动跳过，不影响缠论信号正常显示

---

## 功能需求

### 核心功能

**功能 1：定时舆情搜索任务**

- 描述：基于用户自选股列表，定时通过搜索服务定向搜索每只股票的相关新闻
- 复用已有基础设施：`SearchService`（含 Tavily/Bocha/Anspire 三源 Failover）、`SearchCache`（Redis 缓存 + 防击穿锁）
- 搜索策略：
  - 每只股票构造搜索 query：`"{stock_name} {stock_code} 最新消息"`
  - 搜索参数：`max_results=5`，`days=3`（最近3天）
  - 使用 `SearchService.search()` 方法（已有 Failover 逻辑）
- 调度策略：
  - 交易时段：9:30 / 13:00 / 15:30 三个时间点触发
  - 非交易日：不触发
  - 通过 APScheduler 集成到 FastAPI 进程内（与模块三定时任务同模式）
- 增量去重：
  - 基于新闻 URL 的 SHA-256 hash 去重
  - 已存在的 URL 不重复写入
- 容错：
  - 搜索服务未配置 → 静默跳过，记录 warn 日志
  - 单只股票搜索失败 → 跳过该股，不阻塞其他股票
  - API 调用频率控制：并发数 ≤ 5，避免触发搜索 API 限流

**功能 2：AI 情感分析服务**

- 描述：对每条新闻进行情感分析，输出情感方向和情感得分
- 技术方案：复用已有 `AIService`，新增情感分析提示词模板
- 分析维度：
  - 情感方向：`positive`（正面）/ `neutral`（中性）/ `negative`（负面）
  - 情感得分：-1.0 到 +1.0 的浮点数（-1 为极端负面，+1 为极端正面）
  - 关联行业：从申万31个一级行业中识别该新闻影响的行业
  - 关联股票：识别新闻中提到的A股代码
- 性能优化：
  - 批量分析：将同一只股票的多条新闻合并为一次 LLM 调用（最多5条/批）
  - 结果缓存：分析结果持久化到 `t_stock_sentiment` 表，不重复分析
  - 短文本快速判断：新闻摘要 ≤ 30字时，使用关键词规则快速分类（不调 LLM）
- 提示词模板：

```
你是一位专业的A股舆情分析师。请分析以下新闻对A股市场的影响。

新闻标题：{title}
新闻摘要：{snippet}

请输出以下JSON格式（不要输出其他内容）：
{
  "sentiment": "positive/neutral/negative",
  "score": 0.0到1.0之间的浮点数（正面越高，负面越低，中性接近0），
  "industries": ["行业1", "行业2"],
  "stock_codes": ["代码1"]
}
```

**功能 3：舆情数据 API**

- `GET /api/v1/sentiment/stocks/{code}/overview`：返回指定股票舆情概览（热度、情感综合得分、最近3条新闻）
- `GET /api/v1/sentiment/stocks/{code}/timeline`：返回指定股票舆情时间线（分页，含情感得分）
- `POST /api/v1/sentiment/stocks/batch-overview`：批量获取多只股票舆情概览（自选股列表用）
- `GET /api/v1/sentiment/daily-brief`：获取今日舆情早报
- `POST /api/v1/sentiment/analyze`：对指定新闻触发 AI 情感分析（手动触发）
- 响应格式示例：

```json
GET /api/v1/sentiment/stocks/300750/overview

{
  "code": "300750",
  "name": "宁德时代",
  "heat_level": "hot",
  "sentiment_score": 0.65,
  "sentiment_direction": "positive",
  "news_count_today": 3,
  "latest_news": [
    {
      "title": "宁德时代发布新一代电池技术",
      "url": "https://...",
      "sentiment": "positive",
      "score": 0.8,
      "published_at": "2026-05-11T08:30:00"
    }
  ],
  "updated_at": "2026-05-11T09:30:00"
}
```

**功能 4：舆情早报生成**

- 描述：每日定时聚合用户自选股舆情，生成结构化早报
- 生成逻辑：
  1. 获取用户所有自选股代码
  2. 从 `t_stock_sentiment` 读取昨日至今日舆情数据
  3. 按热度排序（新闻数量 × 情感得分绝对值）
  4. 每只股票生成一句话摘要（新闻标题拼接）
  5. 筛选重大事件（情感得分绝对值 ≥ 0.7）
- 存储方式：写入 `t_sentiment_daily_brief` 表，Redis 缓存当日早报
- 早报格式为 JSON（前端渲染为卡片列表）

**功能 5：舆情+缠论信号共振计算**

- 描述：在模块三缠论信号计算完成后，叠加舆情维度判断共振条件
- 触发时机：模块三 `StrategySignalCalcTask` 完成信号计算后，回调触发
- 共振逻辑：
  - 读取该股近3日舆情情感得分均值
  - 买入信号 + 情感得分 ≥ 0.3 → 标记"强关注"
  - 卖出信号 + 情感得分 ≤ -0.3 → 标记"风险警示"
  - 其他情况 → 不叠加舆情维度
- 共振标记写入 `strategy_signals` 表的扩展字段
- 舆情数据不可用时，共振判断自动跳过（降级为纯缠论信号）

---

## 范围外（本期不做）

| 功能 | 原因 |
|------|------|
| **实时 WebSocket 舆情推送** | MVP先做定时轮询验证价值，实时推送是Phase 2 |
| **用户自定义舆情关键词订阅** | MVP先做基于自选股的自动监测，自定义订阅是Phase 2 |
| **社交媒体舆情（雪球/微博/股吧）** | 数据源接入复杂，MVP先做新闻搜索 |
| **舆情影响力回测**（新闻后N日涨跌幅统计） | 需要历史数据积累，Phase 2 |
| **行业舆情热力图** | 需要全行业舆情覆盖，MVP先聚焦自选股 |
| **舆情自动触发AI分析**（无需用户点击） | 用户的分析习惯需要保留主动权，避免信息轰炸 |
| **邮件/IM推送舆情** | Phase 2 |

---

## 技术约束

### 性能

- 单只股票舆情搜索：≤ 5秒（含三源 Failover）
- 50只自选股批量搜索：≤ 60秒（并发数5）
- 情感分析（单批5条新闻）：≤ 10秒
- 舆情概览 API 响应：≤ 1秒（从 Redis 缓存读取）
- 舆情时间线 API 响应：≤ 2秒

### 成本控制

- 搜索 API 调用：每只股票每次搜索 1 次调用，50只股票 × 3次/日 = 150次/日
- LLM 情感分析：采用批处理（5条/批），50只股票 × 1批/次 × 3次/日 = 150次 LLM 调用/日
- Redis 缓存：舆情概览 TTL 4小时，早报 TTL 当日有效
- 增量去重：基于 URL hash，避免重复搜索和分析

### 数据

- 舆情数据保留 30 天，超过30天的自动清理（APScheduler 定时任务）
- 单只股票每日最多存储 10 条新闻（按情感得分绝对值取 Top 10）
- 情感得分使用 `Decimal` 类型存储（遵循宪章要求）

### 集成

| 集成点 | 方式 | 说明 |
|--------|------|------|
| 搜索服务 | 直接复用 `SearchService` | 已有三源 Failover + 缓存，无需新建 |
| AI 服务 | 直接复用 `AIService` | 新增情感分析提示词模板 |
| 模块二自选股 | API 集成 | 自选股列表展示舆情热度 |
| 模块二个股页 | 前端组件集成 | 新增"舆情动态"标签页 + K线舆情气泡 |
| 模块三信号 | 回调集成 | 缠论信号计算完成后触发共振判断 |
| 模块一分析 | 路由跳转 | 舆情新闻一键触发AI分析 |

### 技术栈

- 搜索：复用 `infrastructure/search/`（Tavily/Bocha/Anspire）
- AI 情感分析：复用 `infrastructure/ai/ai_service.py` + 新增提示词模板
- 定时任务：复用 APScheduler（集成在 FastAPI 进程内）
- 缓存：复用 `infrastructure/cache/redis_cache.py`
- 持久化：MySQL（`t_stock_sentiment`、`t_sentiment_daily_brief`）
- 前端图表：ECharts 5（情感趋势折线图 + K线舆情气泡 `markPoint`）

---

## 后端架构设计

### 分层实现

遵循项目现有 Router → Application → Domain → Infrastructure 四层架构：

```
backend/app/
├── domain/
│   ├── entities/
│   │   └── stock_sentiment.py         # 舆情实体（SentimentDirection枚举、StockSentiment实体）
│   ├── value_objects/
│   │   └── sentiment_result.py        # 情感分析结果值对象
│   ├── repositories/
│   │   └── sentiment_repo.py          # 舆情仓库接口（ABC）
│   └── services/
│       └── sentiment_analyzer.py      # 情感分析领域服务（纯规则，不依赖AI）
│
├── application/
│   ├── use_cases/
│   │   ├── fetch_sentiment.py         # 定时拉取舆情用例
│   │   ├── get_sentiment_overview.py  # 获取舆情概览用例
│   │   ├── get_sentiment_timeline.py  # 获取舆情时间线用例
│   │   ├── generate_daily_brief.py    # 生成每日早报用例
│   │   └── calc_signal_resonance.py   # 计算信号共振用例
│   └── dtos/
│       └── sentiment_dto.py           # 舆情相关 DTO
│
├── infrastructure/
│   ├── ai/
│   │   └── prompts/
│   │       └── sentiment.py           # 情感分析提示词模板
│   ├── db/
│   │   ├── models.py                  # 新增 ORM 模型
│   │   └── migrations/                # Alembic 迁移
│   ├── repositories/
│   │   └── mysql_sentiment_repo.py    # 舆情仓库实现
│   └── search/
│       └── sentiment_fetcher.py       # 舆情搜索编排（基于现有SearchService）
│
├── routers/
│   └── sentiment.py                   # 舆情 API 路由
```

### 数据库表设计

```sql
-- 股票舆情表
CREATE TABLE t_stock_sentiment (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL COMMENT '股票代码',
    stock_name VARCHAR(20) NOT NULL COMMENT '股票名称',
    title VARCHAR(500) NOT NULL COMMENT '新闻标题',
    snippet TEXT COMMENT '新闻摘要',
    url VARCHAR(1000) COMMENT '原文链接',
    url_hash VARCHAR(64) NOT NULL COMMENT 'URL的SHA-256哈希（去重用）',
    source VARCHAR(50) NOT NULL COMMENT '搜索来源（tavily/bocha/anspire）',
    sentiment VARCHAR(10) NOT NULL COMMENT '情感方向：positive/neutral/negative',
    sentiment_score DECIMAL(5,4) NOT NULL COMMENT '情感得分 -1.000 到 +1.000',
    mentioned_industries JSON COMMENT '提及的申万行业列表',
    mentioned_stocks JSON COMMENT '提及的其他股票代码',
    published_at DATETIME COMMENT '新闻发布时间',
    fetched_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '抓取时间',
    -- 审计字段
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    create_user VARCHAR(50) DEFAULT 'system',
    update_user VARCHAR(50) DEFAULT 'system',
    deleted TINYINT NOT NULL DEFAULT 0,
    UNIQUE KEY uk_url_hash (url_hash),
    INDEX idx_stock_date (stock_code, published_at DESC),
    INDEX idx_stock_sentiment (stock_code, sentiment, published_at DESC)
) COMMENT '股票舆情数据表';

-- 舆情每日早报表
CREATE TABLE t_sentiment_daily_brief (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    brief_date DATE NOT NULL COMMENT '早报日期',
    content JSON NOT NULL COMMENT '早报内容（结构化JSON）',
    stock_count INT NOT NULL DEFAULT 0 COMMENT '覆盖股票数量',
    event_count INT NOT NULL DEFAULT 0 COMMENT '重大事件数量',
    -- 审计字段
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    create_user VARCHAR(50) DEFAULT 'system',
    update_user VARCHAR(50) DEFAULT 'system',
    deleted TINYINT NOT NULL DEFAULT 0,
    UNIQUE KEY uk_date (brief_date)
) COMMENT '舆情每日早报表';
```

---

## 前端设计

### 新增组件

遵循现有前端分层（Page → Application → Service）：

```
frontend/src/
├── components/
│   ├── stock/
│   │   ├── SentimentHeatTag.tsx       # 舆情热度标签组件（热点/关注/平静）
│   │   ├── SentimentTimeline.tsx      # 舆情时间线标签页（情感折线图 + 新闻列表）
│   │   ├── SentimentChart.tsx         # 情感趋势折线图（ECharts）
│   │   └── KLineChart.tsx             # 现有组件扩展：新增舆情气泡 markPoint
│   └── layout/
│       └── DailyBriefModal.tsx        # 每日早报弹窗
│
├── services/
│   └── sentimentService.ts            # 舆情 API 服务
│
├── store/
│   └── sentimentStore.ts              # 舆情状态管理
│
└── domain/
    └── types.ts                       # 新增舆情相关类型定义
```

### 新增类型定义

```typescript
// 舆情情感方向
type SentimentDirection = 'positive' | 'neutral' | 'negative';

// 舆情热度等级
type HeatLevel = 'hot' | 'watch' | 'calm';

// 单条舆情新闻
interface SentimentNews {
  id: number;
  title: string;
  snippet?: string;
  url?: string;
  source: string;
  sentiment: SentimentDirection;
  score: number;
  mentioned_industries?: string[];
  mentioned_stocks?: string[];
  published_at: string;
}

// 股票舆情概览（自选股列表用）
interface StockSentimentOverview {
  code: string;
  name: string;
  heat_level: HeatLevel;
  sentiment_score: number;
  sentiment_direction: SentimentDirection;
  news_count_today: number;
  latest_news: SentimentNews[];
  updated_at: string;
}

// 舆情时间线（个股详情页用）
interface SentimentTimelineItem {
  date: string;
  avg_score: number;
  news_count: number;
  news: SentimentNews[];
}

// 每日早报
interface DailyBrief {
  brief_date: string;
  stock_summaries: {
    code: string;
    name: string;
    heat_level: HeatLevel;
    summary: string;
  }[];
  industry_updates: {
    industry: string;
    event: string;
  }[];
  major_events: {
    title: string;
    code: string;
    name: string;
    sentiment: SentimentDirection;
    score: number;
  }[];
}

// 信号共振类型
type ResonanceType = 'strong_buy' | 'risk_warning' | null;
```

### 页面改动清单

| 页面 | 改动点 | 涉及组件 |
|------|--------|---------|
| `WatchlistPage` | 自选股表格新增"舆情"列 + "有舆情"筛选按钮 | `SentimentHeatTag` |
| `StockDetailPage` | 底部标签页新增"舆情动态" | `SentimentTimeline`（含 `SentimentChart`） |
| `StockDetailPage` | K线图新增舆情气泡标注 | `KLineChart`（扩展 markPoint） |
| `AnalysisPage` | 接收路由参数，自动填入新闻+触发分析 | 已有 `AnalysisInput` |
| `AppLayout` | 铃铛通知增加"舆情早报"类型 | `DailyBriefModal` |

---

## MVP 范围 & 分期

### Phase 1（MVP）—— 必须完成

| 功能 | 优先级 | 说明 |
|------|--------|------|
| 定时舆情搜索 | P0 | 基于自选股定时搜索，复用已有 SearchService |
| AI 情感分析 | P0 | 对搜索结果做情感分类，复用已有 AIService |
| 舆情数据 API | P0 | 概览/时间线/批量概览三个核心接口 |
| 自选股舆情热度 | P0 | 自选股列表新增舆情列（Story 1） |
| 个股舆情时间线 | P1 | 个股详情页新增"舆情动态"标签（Story 2） |
| 舆情一键AI分析 | P1 | 舆情新闻一键触发模块一分析（Story 3） |

### Phase 2 —— 体验增强

| 功能 | 优先级 | 说明 |
|------|--------|------|
| K线图舆情气泡 | P1 | K线图标注舆情事件位置（Story 4） |
| 每日舆情早报 | P1 | 自动生成+站内推送（Story 5） |
| 舆情+缠论共振 | P1 | 双信号共振提醒（Story 6） |
| 行业舆情热力图 | P2 | 申万31行业舆情热度色块 |
| 自定义关键词订阅 | P2 | 用户自定义舆情监控关键词 |
| 舆情影响力回测 | P3 | 新闻后N日涨跌幅统计分析 |

---

## 风险评估

| 风险 | 概率 | 影响 | 应对策略 |
|------|------|------|----------|
| 搜索API调用超限（50只×3次/日=150次） | 中 | 高 | 增量去重 + Redis缓存 + 并发控制 ≤5 |
| LLM情感分析准确率不足（< 70%） | 中 | 中 | 短文本用关键词规则兜底；长文本用LLM；Phase 2可引入人工校准 |
| 舆情信息成为噪音（用户关闭功能） | 中 | 高 | 默认只显示"热点"级别；提供开关控制；每股每日最多3条新闻 |
| 搜索服务未配置导致功能不可用 | 低 | 中 | 前端优雅降级（显示"-"）；后端 warn 日志提示配置 |
| 舆情与K线时间对齐偏差 | 低 | 低 | 允许 ±1天容差；以发布日期为准 |
| 新闻URL变化导致去重失效 | 低 | 低 | 同时基于 URL hash + 标题 hash 双重去重 |

---

## 依赖与阻塞项

**依赖：**
- `SearchService`（已实现）：舆情搜索直接复用，无需新建搜索能力
- `AIService`（已实现）：情感分析直接复用，只需新增提示词模板
- 模块二自选股 API（已实现）：`/api/v1/watchlist/groups` 获取自选股列表
- APScheduler（已集成）：定时任务框架已就绪
- Redis 缓存（已实现）：`RedisCache` 类可直接复用

**模块三依赖（Phase 2 联动）：**
- 模块三缠论信号 API（`/api/strategy/{code}/signal`）：信号共振需要读取缠论信号
- 模块三定时任务完成后的回调机制：需与模块三约定回调接口

**已知阻塞项**：暂无

---

## 与现有模块的联动路径汇总

```
舆情监测（模块四）
  │
  ├─→ 模块二（行情数据）
  │     ├─ 自选股列表新增舆情热度列
  │     ├─ 个股详情页新增"舆情动态"标签
  │     └─ K线图新增舆情事件气泡
  │
  ├─→ 模块一（AI分析）
  │     ├─ 舆情新闻一键触发AI深度分析
  │     ├─ 分析来源标注"来自舆情"
  │     └─ 早报中的事件触发AI分析
  │
  ├─→ 模块三（策略监控）
  │     ├─ 缠论信号+舆情情感共振提醒
  │     └─ 自选股信号灯升级显示
  │
  └─→ 全局
        ├─ 每日舆情早报（站内通知）
        └─ 舆情数据写入知识库关联
```

---

*本PRD基于现有代码架构分析编写，所有技术方案均复用已有基础设施（SearchService、AIService、RedisCache、APScheduler），遵循项目宪章（个人投研工具边界、四层架构、禁止跨层调用）。*
