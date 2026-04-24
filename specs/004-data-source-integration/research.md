# Research: 多数据源股票数据体系引入

## Decision 1: 数据持久化方案 — MySQL vs MongoDB

**Context**: 产品规范 (spec.md) 提到使用 MongoDB 存储股票数据集合，但项目当前使用的是 MySQL 作为主库，MongoDB 不存在于代码库中。

### Decision: 使用 MySQL 作为主持久化存储

**Rationale**:
1. 项目宪章明确规定主库为 MySQL，引入 MongoDB 会增加运维复杂度和基础设施成本
2. 当前已有 10 张表基于 MySQL，已有完善的 Alembic 迁移体系
3. 股票数据的结构化特性（基础信息、行情、K线、财务）完全适合关系型存储
4. 市场数据 PRD (`docs/market-data-prd.md`) 同样定义基于 MySQL + Redis 缓存
5. MySQL 8.0+ 支持 JSON 字段，可灵活存储扩展数据

**MySQL 表设计映射** (对应原 MongoDB 集合):
- `stock_basic_info` → `t_stock` (已有, 需扩展字段)
- `market_quotes` → `t_market_quote` (新建)
- `stock_daily_quotes` → `t_stock_daily_quote` (新建)
- `stock_financial_data` → `t_stock_financial` (新建)
- `sync_tasks` → `t_sync_task` (新建)
- `datasource_configs` → `t_datasource_config` (新建)

**Alternatives considered**:
- MongoDB: 放弃，引入额外基础设施，与宪章冲突
- 混合存储 (MySQL + MongoDB): 放弃，当前规模无需 NoSQL

## Decision 2: 数据清洗服务的位置与方式

**Context**: 三个数据源的数据格式不同（Tushare 返回 dict、AKShare 返回 DataFrame、BaoStock 返回 list），需要统一的清洗标准化服务。

### Decision: 在 Domain Services 层实现 DataCleaner

**Rationale**:
1. 数据清洗是领域逻辑，应在 Domain 层实现
2. 清洗规则（代码补零、日期格式化、单位转换、来源标注）是稳定的业务规则
3. 各数据源的 API 客户端在 Application 层负责原始数据获取，清洗交由 Domain 层
4. 清洗后的标准数据模型在各数据源间统一

**清洗流程**:
```
Application 层 (AKShareClient.fetch()) → 原始数据
    ↓
Domain 层 (DataCleaner.clean_basic_info(raw, source="akshare"))
    ↓
标准化实体 (StockBasicInfo entity)
    ↓
Infrastructure 层 (StockDataRepo.upsert(entity))
    ↓
MySQL 存储
```

**Alternatives considered**:
- 在各 API Client 中内嵌清洗逻辑: 放弃，违反 DDD 分层原则
- 独立的中间件/管道: 过度设计，当前场景不需要

## Decision 3: 同步进度推送方案

**Context**: FR-004 要求在同步过程中向用户展示实时进度。

### Decision: 使用 SSE (Server-Sent Events) 推送同步进度

**Rationale**:
1. 项目已有 SSE 基础设施（AI 分析流式输出），前端具备 EventSource 消费能力
2. SSE 适合单向进度推送场景，实现简单
3. 与 WebSocket 相比无需额外连接管理
4. 复用现有的流式输出前端组件逻辑

**SSE 消息格式**:
```
event: sync_progress
data: {"task_id": "...", "source": "tushare", "type": "basic_info", "progress": 45, "total": 5000, "current": 2250, "status": "running"}

event: sync_progress
data: {"task_id": "...", "status": "completed", "record_count": 5000, "duration_ms": 12340}
```

**Alternatives considered**:
- WebSocket: 放弃，项目已有 SSE 基础设施，无需引入新协议
- 轮询 (polling): 放弃，延迟高且浪费资源

## Decision 4: Redis 缓存实现

**Context**: Redis 已配置但未使用，需要为热数据提供缓存层。

### Decision: 实现轻量级 Redis 缓存包装器

**Rationale**:
1. Redis 包已在依赖中，配置已存在，启用成本低
2. 行情数据等热数据适合 Redis TTL 缓存
3. 采用简单的 key-value 缓存模式，不引入复杂模式
4. 缓存未命中时回退到 MySQL 查询

**缓存策略**:
| 数据类型 | Key 格式 | TTL |
|---------|----------|-----|
| 股票行情 | `stock:quote:{code}` | 5 分钟 |
| 股票基础信息 | `stock:basic:{code}` | 24 小时 |
| 数据源配置 | `datasource:config:{type}` | 1 小时 |

**Alternatives considered**:
- 内存缓存 (in-memory): 放弃，不支持多进程部署
- 数据库查询 + 应用层缓存: 放弃，不如 Redis 高效

## Decision 5: 同步任务互斥机制

**Context**: FR-011 要求防止同一数据源的重复同步任务同时执行。

### Decision: 使用数据库状态标记 + 内存锁

**Rationale**:
1. 单进程部署场景下，内存锁（asyncio.Lock per source）足够
2. 任务状态存储在数据库 `t_sync_task` 表中（running 状态）
3. 双重保护：内存锁防止进程内并发，数据库状态防止跨重启后的重复
4. 避免引入 Redis 分布式锁（当前规模不需要）

**Alternatives considered**:
- Redis 分布式锁: 放弃，当前单进程场景不需要
- APScheduler job 级别互斥: 放弃，本功能无定时任务，是手动触发

## Decision 6: 数据源 API 密钥存储

**Context**: FR-006 要求支持前端配置管理 API 密钥。

### Decision: 密钥加密存储 + 前端脱敏展示

**Rationale**:
1. 密钥存储在 MySQL `t_datasource_config` 表中，使用 Fernet 对称加密
2. 加密密钥从环境变量 `DATASOURCE_ENCRYPTION_KEY` 获取
3. API 返回时脱敏展示（如 `ts_xxxx...xxxx`）
4. 前端表单支持新增/编辑/删除配置
5. AKShare 无需密钥，仅需启用/禁用控制

**Alternatives considered**:
- 明文存储: 放弃，违反安全最佳实践
- 纯环境变量: 放弃，不满足前端配置管理需求
