# Implementation Plan: 缠论策略监控与信号回测

**Branch**: `009-chanlun-signal-system` | **Date**: 2026-08-04 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/009-chanlun-signal-system/spec.md`
**详细规则来源**: `docs/v2/strategy-monitor-prd-v2.md`、`docs/v2/backtest-prd-v2.md`

## Summary

为模块三新增规则型缠论策略监控与信号回测能力。后端复用现有「指标计算」范式（纯函数 Domain Service → UseCase 编排 → MySQL Repository → Router + Redis 缓存），新增 `ChanlunService`（分型/笔/线段/中枢/背驰/买卖点，纯函数 + 黄金样本单测）、APScheduler 收盘扫描任务、信号/结构/配置/回测持久化、SSE 进度推送；前端复用 WatchlistPage 列、KLineChart 图层、zustand store、fetch+ReadableStream SSE 范式，新增策略监控页与回测页，并补齐两个跨域能力（K 线定位、`?code=` 预填）。

**关键技术决策**（详见 [research.md](./research.md)）：

1. 30 分钟 K 线**直接从 Sina 拉取（scale=30）并持久化**到既有 `t_stock_daily_quote`（`period='m30'`），而非 spec FR-005 字面要求的「本地 1 分钟聚合」——因为免费源无法提供 3 年 1 分钟历史。⚠️ **此项偏离 spec，需用户确认**。
2. 不新建交易日历模块，改用「数据新鲜度检查」（当日 bar 是否入库）自然过滤节假日。
3. ECharts 沿用已安装的 **v6**（与宪章/CLAUDE.md 标注的 v5 冲突，以实际安装版本为准，文档漂移另记）。

## Technical Context

**Language/Version**: Python 3.10+（后端）、TypeScript + React 18（前端）
**Primary Dependencies**: FastAPI、SQLAlchemy 2.0(async)、APScheduler、aioredis、httpx、Pydantic；前端 antd 5、zustand、echarts 6（命令式）、axios
**Storage**: MySQL（主库，复用 `t_stock_daily_quote`，新增 4 张策略表 + 3 张回测表）、Redis（信号/结构/回测缓存，复用 `RedisCache` 单例）
**Testing**: pytest（后端，缠论纯函数 + 黄金样本）、vitest（前端，扩展现有 KLineChart.test.tsx 模式）
**Target Platform**: Linux 服务器（systemd 部署，复用现有 `upload.py` 流程）、现代浏览器
**Project Type**: web-service（前后端分离，DDD 四层）
**Performance Goals**: 单股日线计算 ≤2s、30 分钟 ≤1s；100 股双周期 ≤120s；50 股 3 年回测 ≤120s；信号 API ≤500ms（缓存命中）；自选股徽标列表 ≤3s
**Constraints**: 收盘确认不重绘；并发 ≤10；回测与监控同引擎；免费数据延迟预留 5 分钟窗口
**Scale/Scope**: 自选股上限 200 只/用户；回测区间 1/3/5 年；信号历史长期留存

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 宪章条款 | 评估 | 结论 |
|---|---|---|
| I. 三模块协同优先 | 归属**模块三（策略监控）**；联动：自选股→信号徽标、信号→K 线定位、信号→AI 个股深度分析、信号→历史回溯 | ✅ 通过 |
| II. 个人投研工具边界 | 无自动交易；全部信号/回测处标注「不构成投资建议」；明示数据延迟与算法简化；不承诺收益 | ✅ 通过（FR-016/SC + 文案门禁） |
| III. 简洁实用 | 复用 indicator/watchlist/sync/SSE 既有范式；30 分钟 K 复用既有表；缠论引擎为纯函数；最小新增 | ✅ 通过 |
| 技术栈 | Python/FastAPI/MySQL/Redis/AKShare/React/antd/Zustand 全部对齐 | ✅ 通过 |
| 架构红线 | 后端分层：`ChanlunService` 纯 Domain、Repository 独占 DB、Router 仅 SSE/鉴权；前端 HTTP 全走 `services/` | ✅ 通过 |
| 数据约束 | 价格用 `Decimal`/`DECIMAL(12,3)`，比例用 `DECIMAL(8,6)`；JSON 仅存结构快照扩展字段 | ✅ 通过 |
| SSE 成对实现 | 复用范式 A（`event:`+`data:`，后台解耦 + Queue），前端 fetch+ReadableStream | ✅ 通过 |
| UI 设计治理 | 遵循 DESIGN.md：antd Card/Table、tabular-nums、Skeleton/Empty/Alert 三态、蓝调阴影、紫主色 | ✅ 通过 |
| 测试门禁 | 缠论引擎纯函数 + 黄金样本单元测试为上线门禁；回测/监控一致性测试 | ✅ 通过 |
| **冲突项：ECharts 版本** | 宪章/CLAUDE.md 标 v5，**实际安装 v6**（`frontend/package.json:16`） | ⚠️ 文档漂移，以实际 v6 为准，建议后续同步宪章标注（非阻断） |

**门禁结论**：无阻断性违反，无需 Complexity Tracking 豁免。ECharts 版本为文档漂移，记录在 research.md，不构成实现障碍。

## Project Structure

### Documentation (this feature)

```text
specs/009-chanlun-signal-system/
├── plan.md              # 本文件
├── spec.md              # /speckit.specify 产出
├── research.md          # Phase 0 决策
├── data-model.md        # Phase 1 实体与表
├── quickstart.md        # Phase 1 运行说明
├── contracts/           # Phase 1 接口契约
│   ├── rest-api.md
│   ├── sse-events.md
│   └── frontend-service.md
├── checklists/
│   └── requirements.md  # /speckit.specify 产出
└── tasks.md             # /speckit.tasks 产出（本命令不创建）
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── domain/
│   │   ├── services/chanlun_service.py          # 新增：纯函数缠论引擎（分型/笔/线段/中枢/背驰/买卖点）
│   │   ├── services/chanlun_divergence.py       # 新增：MACD 面积 + 价格幅度背驰判定（纯函数）
│   │   ├── entities/chanlun.py                  # 新增：Signal/StructureSnapshot/Fractal/Bi/Segment/Zhongshu 实体
│   │   ├── entities/backtest.py                 # 新增：BacktestReport/SignalDetail/Summary 实体
│   │   ├── repositories/chanlun_repo.py         # 新增：ABC 接口
│   │   ├── repositories/backtest_repo.py        # 新增：ABC 接口
│   │   └── models/chanlun_enums.py              # 新增：SignalType/Period/SignalStatus 枚举
│   ├── application/
│   │   ├── use_cases/chanlun_calc.py            # 新增：单股计算编排（读K→引擎→落库），照抄 indicator_calc.py
│   │   ├── use_cases/chanlun_monitor.py         # 新增：扫描全部自选股 + 调度入口 + 重算
│   │   ├── use_cases/chanlun_backtest.py        # 新增：历史重算 + 窗口收益 + 聚合报告
│   │   ├── use_cases/watchlist.py               # 修改：补 get_all_items_by_user(user_id) 去重聚合
│   │   └── dtos/chanlun_dto.py                  # 新增：请求/响应 schema
│   ├── infrastructure/
│   │   ├── db/models.py                         # 修改：加 7 个 ORM 模型（信号/结构/配置/日志/回测报告/明细/汇总）
│   │   ├── db/migrations/versions/{rev}_add_chanlun_tables.py  # 新增 Alembic
│   │   ├── db/migrations/env.py                 # 修改：import 新 ORM 模型
│   │   ├── repositories/mysql_chanlun_repo.py   # 新增
│   │   ├── repositories/mysql_backtest_repo.py  # 新增
│   │   ├── repositories/mysql_watchlist_repo.py # 修改：加 get_all_items_by_user
│   │   ├── scheduler/chanlun_scheduler.py       # 新增：日线 15:40 + 30分钟 8 节点 cron，照抄 event_crawler_scheduler
│   │   ├── market/sina_kline_client.py          # 修改/扩展：补 scale=30 历史 30 分钟 K 拉取
│   │   └── cache/redis_cache.py                 # 复用，不改
│   ├── routers/chanlun.py                       # 新增：REST + SSE，注册到 main.py
│   └── core/config.py                           # 修改：加 chanlun_* 配置项
├── tests/
│   ├── unit/domain/test_chanlun_service.py      # 新增：分层黄金样本单测
│   ├── unit/domain/test_chanlun_divergence.py   # 新增
│   ├── integration/test_chanlun_calc.py         # 新增：读K→信号 端到端
│   └── fixtures/chanlun_golden_samples/         # 新增：人工标注样本（JSON）
└── requirements.txt                              # 视需要（无新重依赖）

frontend/
├── src/
│   ├── pages/
│   │   ├── StrategyMonitorPage.tsx              # 新增：策略监控面板（计算状态 + 重算 + 监控开关入口）
│   │   └── BacktestPage.tsx                     # 新增：回测发起 + 报告（汇总表 + 分布图 + 明细下钻）
│   ├── components/strategy/                     # 新增：SignalBadge / StructureLayer / BacktestSummaryTable / BacktestDetailDrawer
│   ├── components/stock/KLineChart.tsx          # 修改：加 markPoint/markLine 渲染笔/线段/中枢/买卖点 + highlightDate 定位
│   ├── components/layout/AppLayout.tsx          # 修改：启用「策略监控」菜单项
│   ├── pages/WatchlistPage.tsx                  # 修改：加「信号」双周期徽标列 + 筛选
│   ├── pages/StockDetailPage.tsx                # 修改：底部 Tab 加「缠论信号」；接 ?signalDate= 定位
│   ├── pages/StockAnalysisPage.tsx              # 修改：支持 ?code= 预填（FR-017 联动）
│   ├── services/strategyService.ts              # 新增：REST + SSE（fetch+ReadableStream）
│   ├── store/strategyStore.ts                   # 新增：zustand
│   ├── store/stockDetailStore.ts                # 修改：加 highlightDate + signalMarks
│   ├── application/useStrategy.ts               # 新增：SSE 编排 hook
│   └── domain/{types.ts,constants.ts}           # 修改：追加信号/结构/买卖点类型与枚举
└── package.json                                  # 不改（echarts v6 已装）
```

**Structure Decision**: 采用现有 Web 应用双工程结构（`backend/` + `frontend/`），严格遵循既有扁平分层。后端核心是纯函数 `ChanlunService`（对标 `indicator_service.py`），通过 `chanlun_calc` UseCase 编排，落库走新增 Repository；定时任务独立 scheduler 模块对标 `event_crawler_scheduler.py`；前端按 `pages/components/services/store/domain` 分层，新功能集中在新 `components/strategy/` 与两个新页面，对既有 WatchlistPage/StockDetailPage/KLineChart 做**最小侵入式扩展**（新增列/Tab/markPoint/query 参数）。

## Complexity Tracking

> 无宪章违反需豁免，本节留空。

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
