# Product Requirements Document: 行情数据展示 & 数据管理（v2）

**版本**: 2.0
**日期**: 2026-05-11
**说明**: 本文档基于实际代码实现重写，反映模块二和模块三的真实功能。原始需求文档保留在 `docs/market-data-prd.md`。

---

## 执行摘要

面向 A 股散户的行情数据展示与数据管理模块，包含两大部分：

1. **行情数据展示**（模块二）：个股K线、财务数据、自选股管理、行业对比
2. **数据管理**（模块三）：多数据源同步、数据源配置、行情数据采集

与原计划相比，主要差异在于：
- 模块三从"缠论策略监控"变更为"数据与工具"面板，缠论标记为"即将推出"
- 新增多数据源支持（Tushare / AKShare / BaoStock）、数据同步面板、数据源配置管理
- 新增全局股票抽屉、批量行情获取、多级容错机制

---

## 与原计划的核心差异

| 维度 | 原计划 (v1.1) | 实际实现 (v2.0) |
|------|---------------|-----------------|
| 数据源 | AKShare 单源 | Tushare / AKShare / BaoStock 三源可配置 |
| 实时行情 | AKShare 直接获取 | 腾讯财经 + 新浪财经双源容错 |
| 分时数据 | AKShare 单源 | 腾讯 → 新浪 → TwelveData 三级容错 |
| 数据同步 | 无 | 完整数据同步面板（SSE流式进度） |
| 数据源配置 | 无 | 数据源配置管理（API Key 加密存储） |
| 技术指标 | 前端计算 | 后端计算并持久化到数据库 |
| 全局股票抽屉 | 未提及 | 任何页面点击股票代码弹出抽屉查看行情 |
| 批量行情 | 无 | 批量获取多只股票实时行情 |
| 模块三定位 | 缠论策略监控 | 数据与工具面板（缠论即将推出） |

---

## 用户故事 & 验收标准

### Story 1：从其他模块跳转到股票行情

**作为** 正在阅读 AI 分析文章或查看知识库的散户
**我希望** 点击文章中的股票代码后立即看到该股行情
**从而** 不打断阅读节奏，快速判断是否值得进一步研究

**验收标准：**

- [ ] 文章正文、摘要、知识库卡片中出现的股票代码高亮显示
- [ ] 点击股票代码，右侧弹出全局股票抽屉（Drawer），不完全跳页
- [ ] 抽屉展示：股票名称、代码、当前价格、涨跌幅
- [ ] 抽屉内有"查看完整页面"按钮，点击跳转到个股完整详情页
- [ ] 关闭抽屉后回到原页面，操作不被打断

---

### Story 2：个股完整详情页

**作为** 散户
**我希望** 在个股详情页看到完整的技术面+基本面信息
**从而** 做出综合判断

**验收标准：**

- [ ] **顶部价格卡**：股票名称 + 代码 + 实时价格 + 涨跌额/涨跌幅 + 成交量/成交额
- [ ] **K线图区**（页面主体，占 60% 高度）：
  - 支持 4 种周期切换：分时 / 日K / 周K / 月K，默认日K
  - 默认开启 MA5（白）/ MA10（黄）/ MA20（紫）+ 成交量柱
  - 支持在指标栏切换开关 MACD / KDJ
  - 支持鼠标拖动平移、滚轮缩放
  - 鼠标悬停显示 OHLCV 数据
- [ ] **底部标签页**：
  - 基本信息：所属行业、总市值、流通市值、上市日期
  - 财务数据：PE（TTM）/ PB / 营收 / 净利润 / 同比增长率
  - 同行对比：同行业股票涨跌幅/PE/PB/营收/利润横向排名
  - 相关分析：知识库中涉及该股的历史分析文章（标题+摘要+日期），点击跳转知识库
- [ ] 页面右上角有「加入自选股」按钮
- [ ] 有「同步K线」按钮，手动触发该股的数据同步

---

### Story 3：股票搜索

**作为** 散户
**我希望** 输入股票名称或代码搜索
**从而** 快速找到想看的股票

**验收标准：**

- [ ] 股票详情页和自选股页面有搜索框
- [ ] 支持输入股票代码（如"300750"）或名称（如"宁德时代"）
- [ ] 输入后实时展示下拉匹配列表，每项显示：股票名称 + 代码 + 今日涨跌幅
- [ ] 支持模糊匹配（输入"宁德"能找到"宁德时代"）
- [ ] 点击搜索结果进入个股详情页
- [ ] 搜索无结果时显示"未找到相关股票"

---

### Story 4：自选股管理

**作为** 散户
**我希望** 将关注的股票分组管理，并实时查看行情变化
**从而** 快速掌握持仓和观察股的动态

**验收标准：**

- [ ] 支持创建、重命名、删除分组
- [ ] 默认创建一个"观察股"分组
- [ ] 自选股列表每行展示：股票名称 + 代码 + 最新价 + 涨跌幅 + 涨跌额 + 所属行业 + 自选日 + 自选价 + 自选涨幅
- [ ] 交易时段内每 30 秒自动刷新行情（调用批量行情接口）
- [ ] 非交易时段停止刷新
- [ ] 支持从自选股列表直接移除股票
- [ ] 点击任意自选股跳转个股详情页

---

### Story 5：行业导航与对比

**作为** 散户
**我希望** 进入某个行业，看到该行业所有股票的对比数据
**从而** 横向比较，找到行业内估值更低/业绩更好的标的

**验收标准：**

- [ ] 页面左侧有申万 31 个一级行业导航菜单
- [ ] 点击某个行业，右侧展示该行业股票综合对比表，包含列：
  - 股票名称 + 代码
  - 今日涨跌幅（颜色标注）
  - PE（市盈率 TTM）
  - PB（市净率）
  - 近一年营收（亿元）
  - 近一年净利润（亿元）
  - 净利润同比增长率
- [ ] 对比表顶部显示行业今日整体平均涨跌幅
- [ ] 支持按任意列排序（点击列标题升序/降序切换）
- [ ] 默认按今日涨跌幅降序排列
- [ ] 点击任意股票行，弹出全局股票抽屉

---

### Story 6：数据同步

**作为** 使用本工具的散户
**我希望** 通过数据同步面板管理数据源和同步任务
**从而** 确保行情数据是最新的

**验收标准：**

- [ ] 数据同步页面提供数据源选择：Tushare / AKShare / BaoStock
- [ ] 选择数据类型：基础信息 / 实时行情 / 日K线 / 财务数据
- [ ] 点击"开始同步"后，通过 SSE 流式展示同步进度
- [ ] 进度信息包含：已处理数量、成功数量、失败数量
- [ ] 同步完成后显示汇总结果
- [ ] 同步历史列表展示所有历史同步任务，支持分页
- [ ] 失败的任务可点击"重试"

---

### Story 7：数据源配置

**作为** 使用本工具的散户
**我希望** 配置数据源的 API Key 和参数
**从而** 使用 Tushare 等需要 API Key 的数据源

**验收标准：**

- [ ] 数据源配置页面列出所有支持的数据源
- [ ] 每个数据源可配置 API Key（输入框，已配置的 Key 脱敏显示）
- [ ] API Key 使用 Fernet 加密存储在数据库中
- [ ] 支持启用/禁用某个数据源
- [ ] 支持配置数据源优先级

---

## 功能需求

### 核心功能

**功能 1：K线图渲染引擎（ECharts）**
- 技术方案：ECharts 6（`echarts-for-react`），基于 ECharts 5 配置兼容
- 支持 4 种周期：分时（分钟聚合）/ 日K / 周K / 月K
- 内置指标：
  - 均线：MA5（白）/ MA10（黄）/ MA20（紫），默认全开
  - 成交量：柱状图，涨日红色，跌日绿色，默认显示
  - MACD：DIF + DEA + BAR 柱状图，默认关闭
  - KDJ：K + D + J 线，默认关闭
- 交互：鼠标拖动平移、滚轮缩放、悬停显示 OHLCV

**功能 2：多数据源数据获取**
- 三种数据源，优先级可配置：
  - **Tushare**：需 API Key（Fernet 加密存储），支持基础信息/行情/日K/财务
  - **AKShare**：免费，无需 Key
  - **BaoStock**：免费，无需 Key
- 所有数据源统一抽象为 sync_client 接口（SyncExecutor 编排）
- 数据同步后持久化到 MySQL，后续查询走本地数据库

**功能 3：实时行情获取**
- **批量行情**（BatchQuoteClient）：腾讯财经（qt.gtimg.cn）+ 新浪财经（hq.sinajs.cn）双源容错
- Redis 缓存 30 秒 TTL
- 支持批量查询多只股票的实时行情
- 自选股页面使用此接口实现 30 秒自动刷新

**功能 4：分时数据获取**
- 三级容错：腾讯财经 → 新浪财经 → TwelveData
- Redis 缓存 30 秒 TTL
- 聚合为当日分时数据

**功能 5：技术指标计算**
- 后端计算并持久化到 `t_stock_indicator` 表
- MA：MA5 / MA10 / MA20
- MACD：DIF / DEA / BAR
- KDJ：K / D / J
- 存储粒度：按股票代码 + 交易日期 + 周期（daily/weekly/monthly）

**功能 6：全局股票抽屉**
- 全局 Zustand Store（`stockDrawerStore`）管理抽屉状态
- 任何页面点击 `StockCodeLink` 组件打开抽屉
- 抽屉内展示：价格卡片 + K线图 + 基本行情数据

**功能 7：文章-股票关联**
- `t_article_stock` 表：article_id + stock_code + stock_name + sentiment
- AI 分析保存时自动从「推荐关注股票」章节提取股票代码
- 支撑知识库「股票视图」和个股详情页「相关分析」标签的数据查询

**功能 8：申万行业股票映射**
- `t_industry` 表：申万行业树（一级/二级分类）
- `t_stock_industry` 表：股票-行业关联
- 支撑行业对比页面的数据查询

---

## 数据模型

| 表 | 说明 |
|----|------|
| `t_stock` | 股票基础信息（代码/名称/交易所/上市日期/行业/市值） |
| `t_stock_industry` | 股票-行业关联（支持多行业） |
| `t_industry` | 申万行业分类树 |
| `t_stock_daily_quote` | 日K线数据（支持 daily/weekly/monthly 周期） |
| `t_stock_financial` | 财务数据（ROE/净利润/营收/EPS/毛利率/负债率） |
| `t_stock_indicator` | 技术指标（MA/MACD/KDJ） |
| `t_market_quote` | 实时行情缓存（价格/涨跌/成交量/PE/PB） |
| `t_watchlist_group` | 自选股分组 |
| `t_watchlist_item` | 自选股条目（含添加价格和时间） |
| `t_article_stock` | 文章-股票关联（含 sentiment） |
| `t_datasource_config` | 数据源配置（API Key 加密存储） |
| `t_sync_task` | 同步任务记录（状态/进度/耗时） |

---

## 技术架构

### 后端分层

```
Router (stock_data.py / watchlist.py / industry.py / sync.py / datasource.py)
  → UseCase (stock_detail / watchlist / industry / minute_data / indicator_calc)
    → Domain Service (indicator_service / data_cleaner / data_priority)
      → Infrastructure:
          - Market Clients (batch_quote / daily_kline / minute / sina / tencent / twelvedata)
          - Sync Clients (tushare / akshare / baostock + sync_executor)
          - Cache (redis_cache)
          - DB Repositories (mysql_stock_data_repo / mysql_stock_indicator_repo / ...)
```

### 前端分层

```
Page (StockDetailPage / WatchlistPage / IndustryPage / SyncPanel)
  → Store (stockDetailStore / watchlistStore / industryStore / syncStore)
    → Service (stockDataService / watchlistService / industryService / syncService / datasourceService)
      → API (axios instance)
```

### 数据流

```
数据源 (Tushare/AKShare/BaoStock)
  ↓ SyncExecutor 同步
MySQL (持久化)
  ↓ UseCase 查询
Redis Cache (30秒-5分钟 TTL)
  ↓ API 返回
前端 ECharts 渲染
```

---

## API 端点汇总

### 行情数据

| 方法 | 路径 | 功能 |
|------|------|------|
| GET | `/api/v1/stocks/search` | 模糊搜索股票（代码/名称） |
| GET | `/api/v1/stocks/all` | 全部活跃股票列表 |
| POST | `/api/v1/stocks/quotes/batch` | 批量获取实时行情（腾讯+新浪） |
| GET | `/api/v1/stocks/{code}` | 股票基本信息 |
| GET | `/api/v1/stocks/{code}/quote` | 最新行情 |
| GET | `/api/v1/stocks/{code}/daily` | 历史K线（支持日/周/月） |
| GET | `/api/v1/stocks/{code}/financial` | 财务数据 |
| GET | `/api/v1/stocks/{code}/minute` | 当日分时数据（三级容错） |
| GET | `/api/v1/stocks/{code}/indicators` | 技术指标（MA/MACD/KDJ） |
| GET | `/api/v1/stocks/{code}/detail` | 综合详情（聚合接口） |
| GET | `/api/v1/stocks/{code}/related-articles` | 相关分析文章 |

### 自选股

| 方法 | 路径 | 功能 |
|------|------|------|
| GET | `/api/v1/watchlist/groups` | 获取自选股分组列表 |
| POST | `/api/v1/watchlist/groups` | 创建分组 |
| PUT | `/api/v1/watchlist/groups/{id}` | 重命名分组 |
| DELETE | `/api/v1/watchlist/groups/{id}` | 删除分组 |
| POST | `/api/v1/watchlist/groups/{id}/stocks` | 添加股票到分组 |
| DELETE | `/api/v1/watchlist/groups/{id}/stocks/{code}` | 从分组移除股票 |

### 行业

| 方法 | 路径 | 功能 |
|------|------|------|
| GET | `/api/v1/industries` | 一级行业列表 |
| GET | `/api/v1/industries/{code}/stocks` | 行业内股票列表 |

### 数据同步

| 方法 | 路径 | 功能 |
|------|------|------|
| GET (SSE) | `/api/v1/sync/execute` | 执行数据同步（SSE 流式进度） |
| GET | `/api/v1/sync/tasks` | 同步任务历史（分页） |
| POST | `/api/v1/sync/tasks/{id}/retry` | 重试失败任务 |

### 数据源配置

| 方法 | 路径 | 功能 |
|------|------|------|
| GET | `/api/v1/datasources` | 列出数据源配置（Key 脱敏） |
| POST | `/api/v1/datasources` | 创建/更新数据源配置 |
| DELETE | `/api/v1/datasources/{source_type}` | 删除数据源配置 |

---

## 性能约束

| 指标 | 目标 | 说明 |
|------|------|------|
| K线图首次渲染 | ≤2 秒 | 历史数据从 MySQL 读取 |
| 从模块一点击到抽屉展示 | ≤1.5 秒 | 含行情数据获取 |
| 批量行情（50只） | ≤3 秒 | 腾讯+新浪双源容错 |
| 行业对比表加载 | ≤3 秒 | 数据每日缓存 |
| 技术指标查询 | ≤1 秒 | 已持久化到数据库 |
| 分时数据刷新 | 30 秒 TTL | 交易时段自动刷新 |

---

## 范围外（本期不做）

| 功能 | 说明 |
|------|------|
| 缠论策略监控 | 原模块三核心功能，标记为"即将推出" |
| K线画线工具 | 用户明确不需要 |
| Level 2 数据 | 超出免费数据范围 |
| 股票财务深度分析 | 用户财务知识有限 |
| 港股/美股 | 只做 A 股 |
| 实时 WebSocket 推送 | 数据延迟可接受 |
| K线指标自定义参数 | 用默认参数 |
| 复权方式切换 | MVP 默认前复权 |
| 行业热力图 | Phase 2 |

---

## 风险评估

| 风险 | 概率 | 影响 | 应对策略 |
|------|------|------|----------|
| AKShare/Tushare 接口变更或限流 | 中 | 高 | 三数据源互为备份；本地缓存所有历史数据 |
| ECharts K线渲染异常 | 低 | 高 | 使用成熟的 ECharts K线配置模板 |
| 腾讯/新浪行情接口被封 | 中 | 高 | 双源容错 + TwelveData 兜底；Redis 缓存 |
| 数据库数据量增长 | 低 | 中 | 日K约 75 万条/1000只股票，MySQL 可承载；分页查询 |
| API Key 泄露 | 低 | 高 | Fernet 加密存储；展示脱敏；环境变量管理 |

---

*本文档基于代码库实际实现编写，原始需求文档保留在 `docs/market-data-prd.md`。*
