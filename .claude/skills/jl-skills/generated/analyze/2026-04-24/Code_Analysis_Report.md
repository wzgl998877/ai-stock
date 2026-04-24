# TradingAgents-CN MongoDB/Redis 数据流分析报告

**生成日期**: 2026-04-24
**分析目标**: MongoDB 和 Redis 中存储的数据来源、清洗、存储全流程
**分析角色**: 开发人员

---

## 1. 架构概览

### 1.1 技术栈

| 组件 | 用途 | 库 | 模式 |
|------|------|-----|------|
| MongoDB | 主数据库（持久化存储） | `pymongo` (同步)、`motor` (异步) | 集合 + 视图 |
| Redis | 缓存层（热数据） | `redis-py` | TTL 缓存 |
| APScheduler | 数据同步调度 | `APScheduler` | 定时任务 |

### 1.2 配置体系

| 文件 | 职责 |
|------|------|
| `app/core/config.py` | FastAPI 层配置，Pydantic Settings，MONGO_URI/REDIS_URL |
| `app/core/database.py` | 异步 MongoDB/Redis 连接管理，索引/视图创建 |
| `tradingagents/config/database_config.py` | 同步配置读取，get_mongodb_config / get_redis_config |
| `tradingagents/config/database_manager.py` | 智能检测器，自动检测 MongoDB/Redis 可用性 + 降级 |

### 1.3 数据流架构

```
外部 API (Tushare/AKShare/BaoStock/FinnHub/Reddit/爬虫)
        ↓
   APScheduler 定时调度
        ↓
   SyncService (数据同步层)
        ↓
   数据清洗转换 (DataFrame → 标准文档)
        ↓
   MongoDB (L2 持久存储) ←→ Redis (L1 TTL 缓存)
        ↓
   MongoDBCacheAdapter (读取适配器)
        ↓
   应用层 (FastAPI + LangGraph + Streamlit)
```

---

## 2. MongoDB 集合详情

### 2.1 A股核心集合

#### stock_basic_info (股票基础信息)

| 属性 | 值 |
|------|-----|
| 数据来源 | Tushare `stock_basic`、AKShare 东方财富、BaoStock |
| 同步频率 | 每日 2am (Tushare) / 3am (AKShare) / 4am (BaoStock) |
| 唯一索引 | `{"code": 1, "source": 1}` (复合唯一) |
| 清洗规则 | Pydantic → dict, 补零 `.zfill(6)`, 自动标注 source |
| 写入方式 | `update_one({"code": code, "source": source}, {"$set": data}, upsert=True)` |

#### market_quotes (实时行情)

| 属性 | 值 |
|------|-----|
| 数据来源 | Tushare `rt_k`、AKShare 新浪/东财 |
| 同步频率 | 交易时间每 5min (Tushare) / 30min (AKShare) |
| 唯一索引 | `{"code": 1}` |
| 写入方式 | `update_one({"code": code}, {"$set": data}, upsert=True)` |

#### stock_daily_quotes (历史K线)

| 属性 | 值 |
|------|-----|
| 数据来源 | Tushare `daily`、AKShare、BaoStock |
| 同步频率 | 工作日 16:00 (Tushare) / 17:00 (AKShare) / 18:00 (BaoStock) |
| 唯一索引 | `{"symbol": 1, "trade_date": 1, "data_source": 1, "period": 1}` |
| 写入方式 | `bulk_write(ReplaceOne, ordered=False)` 每 200 条 |

#### stock_financial_data (财务数据)

| 属性 | 值 |
|------|-----|
| 数据来源 | Tushare `fina_indicator`/`income`/`balancesheet`、BaoStock |
| 同步频率 | 每周日 (Tushare/AKShare) |
| 写入方式 | `update_one({"code": code, "data_source": source}, upsert=True)` |

#### stock_news (新闻数据)

| 属性 | 值 |
|------|-----|
| 数据来源 | 财经新闻爬虫、Google News |
| 同步频率 | 每 2 小时 |
| 写入方式 | 集合写入 |

### 2.2 美股/港股集合

| 集合 | 数据来源 | 说明 |
|------|---------|------|
| `stock_basic_info_us` | FinnHub, Alpha Vantage | 美股基础信息 |
| `market_quotes_us` | FinnHub | 美股实时行情 |
| `stock_basic_info_hk` | 港股提供商 | 港股基础信息 |
| `market_quotes_hk` | 港股提供商 | 港股实时行情 |
| `social_media_messages` | Reddit API | 美股舆情 |

### 2.3 分析与系统集合

| 集合 | 数据来源 | 说明 |
|------|---------|------|
| `analysis_reports` | LangGraph AI 工作流 | 分析结果存储 |
| `analysis_tasks` | 用户提交分析请求 | 任务状态追踪 |
| `analysis_batches` | 批量分析操作 | 批次分组 |
| `system_configs` | Web UI 配置页 | 系统/数据源配置 |
| `llm_providers` | Web UI 配置页 | 大模型供应商配置 |
| `token_usage` | LLM 调用时记录 | Token 用量与费用 |
| `users` | Web UI 注册 | 用户账户 |
| `notifications` | 系统事件 | 用户通知 |
| `job_status` | 同步任务状态 | 后台任务追踪 |

### 2.4 缓存集合 (DatabaseCacheManager)

| 集合 | 用途 | TTL |
|------|------|-----|
| `stock_data` | 原始行情缓存 | MongoDB 持久化, Redis 6h |
| `news_data` | 新闻数据缓存 | MongoDB 持久化, Redis 24h |
| `fundamentals_data` | 基本面数据缓存 | MongoDB 持久化, Redis 24h |

### 2.5 视图

| 视图 | 来源 | 用途 |
|------|------|------|
| `stock_screening_view` | stock_basic_info + market_quotes + stock_financial_data | 股票筛选查询 |

---

## 3. Redis 缓存策略

### 3.1 缓存模式

```
读取: Redis 优先 → 未命中查 MongoDB → 回写 Redis
写入: MongoDB 持久化 + Redis TTL 缓存 双写
```

### 3.2 TTL 配置

| 数据类型 | Key 格式 | TTL | 说明 |
|---------|----------|-----|------|
| 股票行情 | `stock:{symbol}:{md5}` | 6 小时 | DataFrame JSON |
| 新闻数据 | `news:{symbol}:{md5}` | 24 小时 | 文本 |
| 基本面数据 | `fundamentals:{symbol}:{md5}` | 24 小时 | 文本 |

### 3.3 自动降级

```
Redis 可用 → Redis 缓存
Redis 不可用, MongoDB 可用 → MongoDB 读取
都不可用 → 回退到原始数据源
```

---

## 4. 数据清洗规则详细清单

### 4.1 K线数据 (stock_daily_quotes)

| 字段 | 原始格式 | 清洗规则 | 结果格式 |
|------|---------|---------|---------|
| `code` | 原始代码 | `.zfill(6)` 补零 | `"000001"` |
| `amount` | Tushare: 千元 | `* 1000` | 元 (float) |
| `volume` | Tushare: 手 | `* 100` | 股 (float) |
| `pre_close` | 港股/美股缺失 | `close.shift(1)` | float |
| `pct_chg` | 部分缺失 | `(close - pre_close) / pre_close * 100` | float |
| `trade_date` | 各格式 | `_format_date()` | `"YYYY-MM-DD"` |
| `data_source` | 缺失 | 自动标注 | "tushare"/"akshare"/"baostock" |
| `period` | 参数传入 | 直接使用 | "daily"/"weekly"/"monthly" |
| `market` | 参数传入 | 直接使用 | "CN"/"HK"/"US" |

### 4.2 基础信息 (stock_basic_info)

| 字段 | 清洗规则 |
|------|---------|
| Pydantic 模型 | `model_dump()` / `dict()` 转为 dict |
| `source` | 根据 SyncService 自动填充 |
| `symbol` | 若不存在则 `= code` |
| 数据新鲜度 | 已有数据 < 24h 则跳过更新 |

### 4.3 批量写入机制

```
batch_size = 200 条/批次
写入方式: bulk_write(ReplaceOne, ordered=False)
超时重试: 指数退避 3^n 秒, 最多 5 次
```

---

## 5. 调度任务配置

| 任务 | Tushare | AKShare | BaoStock |
|------|---------|---------|----------|
| 基础信息同步 | 每日 2:00 | 每日 3:00 | 每日 4:00 |
| 实时行情同步 | 交易时间 5min | 交易时间 30min | 不支持 |
| 历史数据同步 | 工作日 16:00 | 工作日 17:00 | 工作日 18:00 |
| 财务数据同步 | 周日 3:00 | 周日 4:00 | - |
| 状态检查 | 每小时 | 每小时 30分 | 每小时 45分 |

---

## 6. 关键代码文件索引

### 6.1 连接与配置

| 文件 | 职责 |
|------|------|
| `app/core/config.py` | FastAPI Settings, MONGO_URI/REDIS_URL |
| `app/core/database.py` | 异步连接管理, 索引/视图创建 |
| `tradingagents/config/database_config.py` | 同步配置读取 |
| `tradingagents/config/database_manager.py` | 自动检测 + 降级 |

### 6.2 数据同步

| 文件 | 职责 |
|------|------|
| `app/worker/tushare_sync_service.py` | Tushare 数据同步 |
| `app/worker/akshare_sync_service.py` | AKShare 数据同步 |
| `app/worker/baostock_sync_service.py` | BaoStock 数据同步 |
| `app/worker/financial_data_sync_service.py` | 财务数据同步 |
| `app/worker/multi_period_sync_service.py` | 多周期 K 线同步 |

### 6.3 数据服务

| 文件 | 职责 |
|------|------|
| `app/services/historical_data_service.py` | 历史数据 CRUD + 标准化 |
| `app/services/stock_data_service.py` | 基础信息/行情服务 |
| `app/services/financial_data_service.py` | 财务数据服务 |
| `app/services/database_screening_service.py` | 数据库筛选服务 |

### 6.4 缓存层

| 文件 | 职责 |
|------|------|
| `tradingagents/dataflows/cache/db_cache.py` | DatabaseCacheManager (MongoDB + Redis 双写) |
| `tradingagents/dataflows/cache/mongodb_cache_adapter.py` | MongoDBCacheAdapter (读取适配器) |
| `tradingagents/config/mongodb_storage.py` | token_usage CRUD |

### 6.5 Web 层

| 文件 | 职责 |
|------|------|
| `web/utils/mongodb_report_manager.py` | 分析报告 CRUD |
| `web/modules/database_management.py` | 数据库管理 UI |

### 6.6 调度与脚本

| 文件 | 职责 |
|------|------|
| `app/core/scheduler.py` | APScheduler 配置 |
| `scripts/config/cleanup_sensitive_in_db.py` | 敏感数据清理 |
| `scripts/akshare_sync_optimized.py` | AKShare 优化同步 |
| `cli/tushare_init.py` | Tushare 数据初始化 |

---

## 7. 变更影响面

### 7.1 风险评估矩阵

| 变更范围 | 影响面 | 风险等级 | 建议 |
|---------|--------|---------|------|
| 新增集合字段 | 所有读取该集合的代码 | 🟠 中 | 保留向后兼容 |
| 删除集合字段 | 视图/CacheAdapter/前端 | 🔴 高 | 标记 deprecated 后观察 |
| 修改数据源优先级 | CacheAdapter 所有方法 | 🟡 中 | 配置化不改代码 |
| 修改清洗规则 | 历史数据一致性 | 🟠 中 | 添加 version 字段 |
| 修改唯一索引 | upsert 逻辑 | 🔴 高 | 先建新索引再删旧 |
| 修改缓存 TTL | 数据实时性 | 🟢 低 | 配置化 |

### 7.2 安全变更模式

```
新增字段: 直接 upsert 添加 → 查询验证 → 完成
删除字段: deprecated 标记 → 观察 → 迁移 → 删除
重命名字段: 新旧双写 → 迁移脚本 → 删除旧字段
修改索引: 新建索引 → 观察性能 → 删除旧索引
```

---

## 8. 总结

### 8.1 数据流特点

1. **多数据源**: Tushare/AKShare/BaoStock 三个来源, 按优先级读取
2. **双层存储**: MongoDB 持久化 + Redis TTL 缓存
3. **自动降级**: MongoDB 不可用时降级到原始数据源
4. **智能调度**: APScheduler 按交易时间/周期自动同步
5. **速率保护**: Tushare 限流器, 交易时间检查, 批量写入重试

### 8.2 关键风险点

1. **Tushare API 限流**: rt_k 接口每小时仅 2 次, 自动切换到 AKShare
2. **MongoDB 连接池**: 最大 100, 最小 10, 超时配置 30s/60s/5s
3. **数据一致性**: 多数据源同时写入需靠 source 字段区分
4. **缓存不一致**: Redis 过期后从 MongoDB 回写, 可能读到旧数据
