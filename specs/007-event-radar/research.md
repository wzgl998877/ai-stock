# Research: 投资事件影响雷达

**Branch**: `007-event-radar` | **Date**: 2026-05-11

## 研究任务 1: 财联社信息源接入方案

**Decision**: 使用财联社（cls.cn）的 RSS/HTTP API 接入快讯数据

**Rationale**: 财联社是国内最快的财经快讯来源之一，提供结构化的快讯数据。优先使用 HTTP API 方式（JSON 响应），RSS 作为备选。控制请求频率 ≥ 10 分钟间隔避免反爬。

**Alternatives Considered**:
- HTML 爬取：反爬风险最高，需处理验证码和 IP 封禁，不建议
- 第三方聚合 API（如聚合数据等）：需额外付费，增加依赖，不优先考虑
- 搜索引擎替代：现有 Tavily/Anspire/Bocha 可兜底，但时效性不如专用信息源

**技术细节**:
- 财联社快讯 API 通常返回 JSON 格式，包含 title、content、ctime、source 等字段
- 需实现 `BaseEventProvider` 抽象接口的 `fetch_latest()` 方法
- 异常处理：API 不可用时 fallback 到搜索引擎
- 响应数据需清洗：去除 HTML 标签、截断超长内容

## 研究任务 2: 事件去重算法选择

**Decision**: URL MD5 精确去重 + Jaccard 相似度标题去重（阈值 0.6）

**Rationale**:
- URL hash 是最精确的精确去重手段，O(1) 查询
- Jaccard 相似度比分词+TF-IDF 更轻量，对中文短文本（新闻标题 ≤ 50 字）效果足够
- 阈值 0.6（而非 0.7）偏保守，宁可多保留也不误合并不同事件
- 项目已有 `domain/services/similarity.py` 可参考

**Alternatives Considered**:
- TF-IDF + 余弦相似度：更精确但对短文本优势不明显，且需引入 jieba 分词增加复杂度
- LLM 判断：准确率最高但成本高、延迟大，不适合去重环节
- SimHash：适合大规模文档去重，但我们的场景（每次采集 ≤ 50 条）规模太小

## 研究任务 3: APScheduler 集成方式

**Decision**: 在 FastAPI lifespan 中启动 APScheduler BackgroundScheduler

**Rationale**:
- APScheduler 已在 `requirements.txt` 中声明但未集成
- 在 `backend/app/main.py` 的 `lifespan` 函数中启动 `BackgroundScheduler`，与现有 LangGraph 图初始化同层
- 使用 `AsyncIOScheduler` 以兼容 FastAPI 的 async 环境
- 调度任务注册在独立的 `infrastructure/scheduler/event_crawler_scheduler.py` 中

**Alternatives Considered**:
- Celery：重量级，需要 Redis broker，当前规模不需要
- 系统 cron：不与 FastAPI 进程共享上下文，无法复用 DB 连接
- 简单 asyncio.create_task：无持久化、无调度策略，不适合生产

**集成模式**:
```python
# 在 lifespan 中
scheduler = AsyncIOScheduler()
scheduler.add_job(crawl_and_process, 'cron', minute='*/10', ...)  # 交易时段
scheduler.add_job(crawl_and_process, 'cron', hour='*/1', ...)     # 非交易时段
scheduler.add_job(generate_morning_briefing, 'cron', hour=6, minute=30)  # 晨报
scheduler.start()
```

## 研究任务 4: 影响判断引擎设计

**Decision**: 两阶段判断——规则引擎（快速路径）+ LLM 兜底（低置信度路径）

**Rationale**:
- 80%+ 的新闻可通过关键词规则快速判断（"涨停""利好""制裁""下跌"等）
- 规则引擎延迟 < 10ms，LLM 调用延迟 1-3s
- 仅对规则引擎置信度 < 0.6 的事件调用 LLM，预估 ≤ 20% 的新闻
- 复用现有 `domain/services/metadata_extractor.py` 的股票/行业提取能力

**规则引擎设计**:
- 利好词汇库：涨停、利好、增长、超预期、获批、补贴、上调、突破等
- 利空词汇库：跌停、利空、下降、不及预期、制裁、限制、下调、违约等
- 计算逻辑：匹配词汇数量 → 加权得分 → 映射为 positive/negative/neutral + confidence
- 事件重要性判断：source_count ≥ 3 → high；出现"重大""突发""紧急"等词 → high

**LLM 兜底**:
- 复用 `infrastructure/ai/ai_service.py` 的 `generate_title_and_summary` 方法模式
- Prompt 模板放入 `infrastructure/ai/prompts/impact_assessment.py`
- 输入：事件标题 + 摘要；输出：JSON {sentiment, confidence, reason, importance}

## 研究任务 5: 前端影响雷达页面设计

**Decision**: 遵循现有 DESIGN.md 规范，卡片化布局，Ant Design 5 组件

**Rationale**:
- 项目使用 Ant Design 5 的 Stripe 风格设计系统
- 参考现有 `WatchlistPage.tsx`（表格增强）和 `KnowledgePage.tsx`（卡片化布局）的设计模式
- 新页面 `EventRadarPage.tsx` 放在 `pages/` 目录
- 新组件放在 `components/event-radar/` 目录
- 遵循前端分层：Page → Store (Zustand) → Service → API

**组件拆分**:
- `ImpactEventCard`：单张影响事件卡片（Ant Card），展示标题/来源/时间/影响股票/操作按钮
- `ImpactStatsCard`：影响概览统计卡片（Ant Statistic）
- `EventDetailDrawer`：事件详情抽屉（Ant Drawer），三段式布局
- `AlertDrawer`：预警抽屉（Ant Drawer + Ant Badge + Ant List）
- `MorningBriefingModal`：晨报弹窗（Ant Modal），卡片化内容
- `WatchlistImpactColumn`：自选股影响列（Ant Tag + Ant Popover）
- `AlertBell`：铃铛预警图标（Ant Badge + Ant BellOutlined）

## 研究任务 6: 知识库联动匹配策略

**Decision**: 基于行业 + 股票代码的事件-文章关联匹配

**Rationale**:
- 最简单可靠的匹配方式：事件关联的行业/股票 ∩ 文章关联的行业/股票 → 关联度
- 关联度计算：交集大小 / 并集大小（Jaccard），≥ 0.3 则关联
- 不需要 LLM 参与匹配，纯集合运算，延迟 < 5ms
- 匹配结果在事件详情 Drawer 的"知识库关联"区域展示

**数据来源**:
- 事件的行业/股票：来自 `t_impact_event.affected_industries` 和 `t_impact_event.affected_stocks`
- 文章的行业/股票：来自 `t_article_industry` 和 `t_article_stock`（现有表）
- 匹配查询：SQL JOIN + JSON 函数，在 Repository 层完成
