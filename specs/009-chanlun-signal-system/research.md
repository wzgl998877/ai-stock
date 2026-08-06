# Phase 0 Research: 缠论策略监控与信号回测

**Date**: 2026-08-04
**目的**: 解决 Technical Context 中的所有 NEEDS CLARIFICATION 与冲突项，为 Phase 1 设计定型。每条给出「决策—理由—备选」。

---

## D1. 30 分钟 K 线数据来源（⚠️ 偏离 spec FR-005，需用户确认）

**背景**：spec FR-005 与用户在 PRD 访谈中选择「本地分钟聚合」。但代码探索确认：

- 现网**只缓存当日分时、不持久化任何历史分钟**（`app/domain/entities/minute_quote.py:1-16` 注释明确「仅 Redis 缓存」；无 `MinuteQuoteModel`、无 minute Repository、`DataType` 枚举无 MINUTE）。
- 免费源 Sina `getKLineData(scale=1)` 的 1 分钟历史**条数受限**（通常近 1000-2000 根），**无法回补 3 年 1 分钟数据**。3 年 × 1 股 × 240 分钟/天 × 250 天 ≈ 18 万根/股，50 股即 900 万根，存储与拉取均不现实。

因此 spec FR-005 字面要求对历史数据**不可行**。

**决策**：

- **历史回补 + 日常增量**：直接从 Sina 拉取 **30 分钟 K 线（scale=30）**，持久化到**既有 `t_stock_daily_quote`** 表，`period='m30'`（该表 `period` 列已支持 daily/weekly/monthly，扩展一个枚举值即可，复用既有 Repository/缓存失效逻辑）。
- 复用 `SinaSyncClient._SCALE_MAP`（`sina_sync_client.py:35-39`）已揭示的 scale=30 路径，在 `sina_kline_client.py` 扩展 `fetch(code, period='m30')`。
- 时间戳取**区间结束时刻**（10:00/10:30/.../15:00 共 8 根/交易日），前复权口径与日线一致（Sina scale 系列默认前复权）。

**理由**：

1. **KISS**：复用既有表、Repository、Redis 失效范式，零新增表。
2. **可行性**：Sina scale=30 可拿数年历史，免费、稳定（已被 `SinaSyncClient` 用于 weekly/monthly）。
3. **目标等价**：FR-005「本地聚合」的真实目标是「可回放、多源一致、口径统一」——单一源拉取并持久化同样达成，且更可审计。
4. **存储量级合理**：3 年 × 1 股 ≈ 6000 根 30 分钟 K，50 股 ≈ 30 万根，MySQL 轻松承载。

**备选（已否决）**：

- A. 真正本地 1 分钟聚合：历史不可行（免费源拿不到 3 年 1 分钟），否决。
- B. 新建 `t_stock_kline_30m` 独立表：与既有 `t_stock_daily_quote` 重复，违反 KISS，否决。
- C. 用 Tushare 30 分钟（需 Pro 积分）：增加 Key 依赖与成本，且现有体系 Sina 已可用，否决。

**待确认**：此决策改变 spec FR-005 表述。若用户坚持「本地聚合」，则需降级为「仅当日盘中由 1 分钟聚合、历史不回测 30 分钟」——但这会使 30 分钟回测样本极少。**推荐采用本决策**。

---

## D2. 交易日历与节假日判断

**背景**：现网无交易日历模块，仅靠 cron `day_of_week="mon-fri"`（`event_crawler_scheduler.py:105`）。spec 隐含需要精确交易日判断。

**决策**：**不新建交易日历模块**。改用「数据新鲜度检查」：

- 日线任务 cron 设 `mon-fri 15:40`；执行时对每只股票检查「最新日 K 日期是否 ≥ 今日」。节假日无新 bar → 该股跳过并在日志记录 `no_new_data`，不报错。
- 30 分钟任务 cron 设 8 个时点（10:05/10:35/11:05/11:35/13:35/14:05/14:35/15:05）；同样以「最新 30 分钟 bar 时间戳是否推进」判断是否计算。

**理由**：节假日自然无 bar，新鲜度检查即等价于交易日判断，零新增依赖，符合 KISS。后续如需精确日历可引入 AKShare `tool_trade_date_hist_sina()`，但 MVP 不做。

**备选**：引入交易日历表/接口——增加数据同步与维护成本，MVP 不必要，否决。

---

## D3. ECharts 版本冲突（文档漂移）

**背景**：宪章 `constitution.md:37` 与 `CLAUDE.md` 标 ECharts 5；但 `frontend/package.json:16` 实际安装 `echarts:^6.0.0`，且 `docs/v2/market-data-prd-v2.md:179` 也写 ECharts 6。KLineChart 用**命令式** echarts API（非 echarts-for-react，虽已装）。

**决策**：**沿用已安装的 v6**，命令式风格不变。缠论结构图层通过 `markPoint`/`markLine`/`custom series` 叠加到既有 grid0，与现有 MA/MACD 叠加方式一致。文档漂移已同步（T062）：`constitution.md` 与根/`docs/CLAUDE.md` 技术栈统一改为 **ECharts 6**，与 `package.json` 实际安装版本一致。

**理由**：降级 v5 会破坏现有 K 线与全部图表，风险远大于收益；v6 命令式 API 与 v5 基本兼容。建议后续单独提 PR 同步宪章标注。

---

## D4. K 线定位能力（信号→K 线，新能力）

**背景**：探索确认「定位到某根 K 线」**当前不存在**——`StockCodeLink`/`stockDrawerStore` 仅收 `code`，路由 `/market/stock/:code` 无 query，KLineChart 无高亮 props（`StockCodeLink.tsx:12-38`、`stockDetailStore.ts`）。

**决策**：最小扩展三处：

1. **路由**：`/market/stock/:code?signalDate=YYYY-MM-DD&period=daily|m30`（向后兼容，无参即原行为）。
2. **store**：`stockDetailStore` 加 `highlightDate?: string`、`signalMarks?: MarkPoint[]`；`fetchKlineData` 后若 `highlightDate` 落在区间内则传给图表。
3. **KLineChart**：新增 `signalMarks`/`highlightDate` props，渲染为 `markPoint`（买卖点箭头）+ `markLine`（笔/线段）+ `markArea`（中枢区间）；`highlightDate` 用 `dataZoom` startValue/endValue 定位。

**理由**：复用 echarts 原生 markPoint/markLine/markArea，零新增依赖；向后兼容不破坏既有调用。

---

## D5. `?code=` 预填 AI 个股分析（FR-017 联动）

**背景**：`StockAnalysisPage` 仅支持 `?recordId=`（`:426`），无 `?code=` 预填入口。

**决策**：在 `StockAnalysisPage` 挂载 effect 里，无 `recordId` 时检查 `searchParams.get('code')`，存在则调一个新 store action `setStock(code, name)`（复用 `StockSearchInput` 选中逻辑）预填。信号徽标点击跳转 `navigate('/stock-analysis?code=${signal.stockCode}')`。

**备选**：走全局抽屉 `StockDetailDrawer`——但用户诉求是「深度分析」而非看行情，故直达分析页更贴合 FR-017。

---

## D6. `isMarketOpen()` 双实现统一

**背景**：存在两套 `isMarketOpen()`——`WatchlistPage.tsx:51-59`（本地时区）与 `stockDetailStore.ts:69-82`（北京时区），口径不一致。

**决策**：新建 `frontend/src/utils/marketTime.ts` 统一导出 `isMarketOpen()`（北京时区，A 股 9:30-11:30/13:00-15:00）与 `isTradingDay()`（周一-周五，与 D2 一致，不依赖日历模块）。WatchlistPage、stockDetailStore、新策略相关代码统一引用，删除重复实现。

**理由**：消除双实现漂移；缠论刷新时点必须与 A 股时段一致。

---

## D7. 缠论算法：自研纯函数 vs 第三方库

**背景**：spec 要求「固定、可测试、版本化」的主流缠论口径。

**决策**：**自研纯函数 `ChanlunService`**（对标 `indicator_service.py`），分层实现：包含处理 → 分型 → 笔 → 线段（特征序列法）→ 中枢 → 背驰（`chanlun_divergence.py`，MACD 面积 + 价格幅度双条件）→ 一/二/三类买卖点。每层独立单元测试 + 黄金样本（`tests/fixtures/chanlun_golden_samples/`）。

**理由**：

1. 现有第三方缠论库（如 `chan.py`）口径不一定与 PRD「算法口径」一致，且引入外部依赖后难以保证「版本化固定口径」。
2. 纯函数易测、可回放、零 IO，完全契合宪章 Domain 层约束。
3. 黄金样本集是上线门禁，自研可控。

**备选**：用 `chan.py` 等库——口径不可控、与 PRD 可能冲突，否决；可作黄金样本对照参考的「第三方实现」之一用于验收。

---

## D8. MACD 数据来源（背驰判定依赖）

**背景**：背驰判定需 MACD 面积。现网已持久化 MACD 到 `t_stock_indicator`（DIF/DEA/BAR，`indicator_service.py`，参数 12/26/9，与 PRD 一致）。

**决策**：`chanlun_divergence.py` 输入直接接收 **MACD BAR 序列**（由 UseCase 从 `t_stock_indicator` 读取后传入），**不在缠论引擎内重复计算 MACD**。

**理由**：单一数据源、避免双份计算漂移、复用既有持久化结果。若某股指标未算，UseCase 先触发指标计算（复用 `IndicatorCalcUseCase`）。

---

## D9. 用户 ID 类型对齐

**背景**：现网 `user_id` 类型不一致——`t_user` String32、`t_watchlist_group` String64。

**决策**：新表（策略配置、回测报告）`user_id` 统一用 **String32** 对齐 `t_user`；查询用 `core/deps.py:get_current_user` 注入的 `current_user.user_id`，与 watchlist 一致做归属校验。

---

## D10. 回测与监控一致性保证（SC-005）

**背景**：SC-005 要求回测与监控对同一股票同一区间信号 100% 一致。

**决策**：回测 UseCase **直接调用** `ChanlunService`（与监控同一个纯函数），仅输入区间不同；信号唯一键（股票+周期+类型+信号时间+算法版本）共用。新增一致性集成测试：对黄金样本股，监控增量结果与回测全量结果比对。

**理由**：物理共用同一函数是唯一可靠的 100% 一致保证。

---

## 总结

所有 NEEDS CLARIFICATION 已定型。**唯一需用户拍板的是 D1**（30 分钟数据改直接拉取而非本地聚合）——因其偏离 spec FR-005。D2-D10 均为有合理默认的工程决策，无需用户介入。
