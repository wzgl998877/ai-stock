# Research: 股票详情页与行情数据展示

**Feature**: 006-stock-detail-kline
**Date**: 2026-04-30
**Status**: Complete

---

## 1. 现有系统调研

### 1.1 后端已有能力

通过代码审查，模块二已有以下基础能力：

| 组件 | 状态 | 路径 |
|------|------|------|
| Stock Data Router | ✅ 存在 | `backend/app/routers/stock_data.py` |
| StockDataRepository (Domain Interface) | ✅ 存在 | `backend/app/domain/repositories/stock_data_repo.py` |
| MySQLStockDataRepository | ✅ 存在 | `backend/app/infrastructure/repositories/mysql_stock_data_repo.py` |
| 基础信息接口 | ✅ 存在 | `GET /api/v1/stocks/{code}` |
| 实时行情接口 | ✅ 存在 | `GET /api/v1/stocks/{code}/quote` |
| 日K数据接口 | ✅ 存在 | `GET /api/v1/stocks/{code}/daily` |
| 财务数据接口 | ✅ 存在 | `GET /api/v1/stocks/{code}/financial` |
| Redis缓存 | ✅ 存在 | `backend/app/infrastructure/cache/redis_cache.py` |
| AKShare客户端 | ✅ 存在 | `backend/app/application/sync/akshare_client.py` |

**已有数据库表**（通过 migration a1b2c3d4e5f6）：
- `t_stock` — 股票基础信息
- `t_market_quote` — 实时行情
- `t_stock_daily_quote` — 日K/周K/月K数据
- `t_stock_financial` — 财务数据

**缺失能力**：
- 分时数据（分钟级）存储与查询
- 自选股分组管理
- 申万行业-股票映射
- 文章-股票关联
- 股票搜索（模糊匹配）
- 技术指标计算服务（MA/MACD/KDJ）

### 1.2 前端已有能力

| 组件 | 状态 | 路径 |
|------|------|------|
| StockDataService | ✅ 存在 | `frontend/src/services/stockDataService.ts` |
| API 封装 | ✅ 存在 | `frontend/src/services/api.ts` |
| StockCodeLink 组件 | ✅ 存在 | `frontend/src/components/common/StockCodeLink.tsx` |
| IndustryTag 组件 | ✅ 存在 | `frontend/src/components/common/IndustryTag.tsx` |
| Zustand Store | ✅ 存在 | `frontend/src/store/` |

**缺失能力**：
- 个股详情页（Page）
- K线图组件（ECharts candlestick）
- 自选股管理页面
- 行业导航与对比表
- 搜索下拉组件
- 侧边栏抽屉（模块一联动）

---

## 2. 技术选型决策

### 2.1 K线图渲染

**Decision**: ECharts 5 Candlestick + 多 Grid 布局

**Rationale**:
- 项目技术栈已包含 ECharts 5（见 constitution.md）
- ECharts 5 原生支持 K线图（candlestick）、MA均线、MACD、KDJ、成交量
- 多 Grid 布局可将主图（K线）和副图（MACD/KDJ/成交量）垂直排列
- 支持 dataZoom 实现拖动平移和滚轮缩放
- 中文生态成熟，文档完善

**Alternatives considered**:
- TradingView Lightweight Charts：功能强但社区版限制多，需额外引入依赖
- AntV G2Plot：Ant Design 生态但K线图功能不如ECharts成熟
- 自研 Canvas：成本过高，没必要

### 2.2 技术指标计算

**Decision**: 前端计算 MA，后端计算 MACD/KDJ

**Rationale**:
- MA（均线）: 纯数学运算，前端计算可减少网络传输，ECharts 可直接消费
- MACD/KDJ: 涉及较复杂公式，后端统一计算可复用、可缓存、可测试
- 后端计算后缓存结果，不同用户查看同一只股票时共享计算结果

**计算位置**:
| 指标 | 计算位置 | 说明 |
|------|----------|------|
| MA5/MA10/MA20 | 前端 | 简单滑动平均，ECharts 内置或前端即时计算 |
| 成交量 | 后端 | 直接返回原始数据 |
| MACD | 后端 | 涉及EMA、DIF、DEA、MACD柱，统一计算服务 |
| KDJ | 后端 | 涉及RSV、K、D、J值，统一计算服务 |

### 2.3 分时数据策略

**Decision**: 交易时段每15分钟从AKShare拉取，Redis缓存15分钟；不持久化到MySQL

**Rationale**:
- 分时数据量大（每天240条/股），MySQL存储价值低
- 用户主要关注当日分时，历史分时极少回看
- Redis缓存足够支撑当日访问，收盘后失效
- 与PRD中"分时数据不持久化"一致

### 2.4 股票搜索实现

**Decision**: 后端全量股票列表接口 + 前端本地模糊匹配

**Rationale**:
- A股总数量约5000+，数据量小（名称+代码+行业）
- 前端缓存全量列表后可实现即时响应（<100ms）
- 避免频繁后端请求，减少AKShare调用压力
- 后端只需提供一次性全量股票列表接口（带缓存）

### 2.5 自选股分组存储

**Decision**: MySQL + user_id 关联

**Rationale**:
- 数据量小（每用户最多10组×100股=1000条）
- 需要持久化（跨设备同步）
- MySQL已有用户体系，自然关联

---

## 3. 模块间接口调研

### 3.1 模块一 → 模块二

**已有机制**: `frontend/src/components/common/StockCodeLink.tsx` 已存在股票代码高亮组件

**需要新增**:
- StockCodeLink 点击事件 → 触发侧边栏抽屉打开 → 传递 stock_code
- 模块一知识库文章 → 模块二"相关分析"标签的数据关联

### 3.2 模块二 → 模块一

**需要新增**: "相关分析"标签中点击文章 → 跳转到模块一知识库并定位展开该文章

**实现方式**: 前端路由跳转（如 `/knowledge?article_id=xxx&highlight=true`）

### 3.3 模块三 → 模块二

**已有约定**: 模块三提供 `/api/strategy/{code}/signal` 接口

**当前处理**: 模块二自选股列表中信号灯字段先用 "-" 占位，待模块三接入后替换

---

## 4. 数据库变更调研

### 4.1 需要新增表

1. **t_watchlist_group** — 自选股分组
2. **t_watchlist_item** — 自选股条目（关联分组+股票）
3. **t_industry_stock** — 行业-股票映射（申万一级）
4. **t_article_stock_relation** — 文章-股票关联
5. **t_stock_indicator** — 技术指标缓存（MACD/KDJ等）

### 4.2 需要扩展表

1. **t_stock** — 增加 industry_code（申万一级行业代码）

### 4.3 已有表可直接使用

1. **t_market_quote** — 实时行情（需扩展 PE/PB 字段）
2. **t_stock_daily_quote** — 日K/周K/月K
3. **t_stock_financial** — 财务数据

---

## 5. 风险评估

| 风险 | 概率 | 影响 | 缓解策略 |
|------|------|------|----------|
| ECharts K线复杂配置 | 中 | 高 | 先用官方demo验证，再集成 |
| AKShare分时数据格式不一致 | 中 | 中 | 做数据清洗适配层 |
| 技术指标公式正确性 | 低 | 高 | 与主流平台（同花顺）结果比对验证 |
| 行业股票数量过多渲染卡顿 | 低 | 中 | 对比表分页（每页20条） |

---

## 6. NEEDS CLARIFICATION 解决结果

本次调研未发现需要澄清的技术问题。所有技术选型基于项目已有技术栈和业界最佳实践，决策路径清晰。
