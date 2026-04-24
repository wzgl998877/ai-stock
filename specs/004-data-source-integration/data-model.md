# Data Model: 多数据源股票数据体系

## Entity: DataSourceConfig (数据源配置)

**Table**: `t_datasource_config`

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| id | INT (PK, AUTO_INCREMENT) | No | 主键 |
| source_type | VARCHAR(20) | No | 数据源类型: `tushare`, `akshare`, `baostock` |
| api_key | VARCHAR(512) | Yes | API 密钥（Fernet 加密存储） |
| is_enabled | BOOLEAN | No | 是否启用, 默认 true |
| priority | INT | No | 优先级 (数值越小优先级越高, 默认 99) |
| config_json | JSON | Yes | 扩展配置（如 API 地址、超时设置） |
| create_time | DATETIME | No | 创建时间 |
| update_time | DATETIME | No | 更新时间 |
| create_user | VARCHAR(50) | Yes | 创建人 |
| update_user | VARCHAR(50) | Yes | 更新人 |

**Unique Index**: `uk_source_type` (`source_type`)
**Validation**: `source_type` 必须为 `tushare`、`akshare` 或 `baostock`；`priority` > 0

---

## Entity: SyncTask (同步任务)

**Table**: `t_sync_task`

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| id | INT (PK, AUTO_INCREMENT) | No | 主键 |
| task_id | VARCHAR(36) | No | 任务 UUID |
| source_type | VARCHAR(20) | No | 数据源类型 |
| data_type | VARCHAR(30) | No | 数据类型: `basic_info`, `market_quote`, `daily_quote`, `financial` |
| status | VARCHAR(20) | No | 状态: `pending`, `running`, `completed`, `failed` |
| total_count | INT | Yes | 预计处理数量 |
| processed_count | INT | Yes | 已处理数量 |
| success_count | INT | Yes | 成功写入数量 |
| fail_count | INT | Yes | 失败数量 |
| error_message | TEXT | Yes | 错误信息 |
| start_time | DATETIME | Yes | 开始时间 |
| end_time | DATETIME | Yes | 结束时间 |
| duration_ms | INT | Yes | 耗时（毫秒） |
| create_time | DATETIME | No | 创建时间 |

**Index**: `idx_source_status` (`source_type`, `status`), `idx_create_time` (`create_time`)
**Validation**: `status` 状态机: `pending` → `running` → `completed`/`failed`
**State Transitions**:
- `pending` → `running`: 开始执行
- `running` → `completed`: 执行成功
- `running` → `failed`: 执行失败
- `failed` → `pending`: 手动重试

---

## Entity: StockBasicInfo (股票基础信息)

**Table**: `t_stock` (已有，需扩展)

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| id | INT (PK, AUTO_INCREMENT) | No | 主键 |
| code | VARCHAR(10) | No | 股票代码 (6位补零, 如 `000001`) |
| name | VARCHAR(100) | No | 股票名称 |
| exchange | VARCHAR(20) | Yes | 交易所 (SSE, SZSE, HKEX, NASDAQ 等) |
| market_type | VARCHAR(20) | Yes | 市场类型: `CN_A`, `CN_KC`, `HK`, `US` |
| industry | VARCHAR(50) | Yes | 所属行业 |
| list_date | DATE | Yes | 上市日期 |
| is_active | BOOLEAN | No | 是否上市交易中, 默认 true |
| data_source | VARCHAR(20) | Yes | 数据来源标注 |
| update_time | DATETIME | No | 更新时间 |

**Unique Index**: `uk_code_source` (`code`, `data_source`)
**Validation**: `code` 必须为 6 位数字（A股），需 `.zfill(6)` 补零

**扩展字段** (相对于现有 `t_stock`):
- 新增 `data_source` 字段
- 新增 `market_type` 字段
- 修改唯一约束为 `(code, data_source)` 复合唯一索引

---

## Entity: MarketQuote (实时行情)

**Table**: `t_market_quote` (新建)

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| id | INT (PK, AUTO_INCREMENT) | No | 主键 |
| code | VARCHAR(10) | No | 股票代码 |
| price | DECIMAL(12, 3) | Yes | 当前价格 |
| change_pct | DECIMAL(8, 2) | Yes | 涨跌幅 (%) |
| change_amount | DECIMAL(12, 3) | Yes | 涨跌额 |
| volume | DECIMAL(18, 0) | Yes | 成交量 (股) |
| amount | DECIMAL(18, 2) | Yes | 成交额 (元) |
| open_price | DECIMAL(12, 3) | Yes | 今开价 |
| high_price | DECIMAL(12, 3) | Yes | 最高价 |
| low_price | DECIMAL(12, 3) | Yes | 最低价 |
| pre_close | DECIMAL(12, 3) | Yes | 昨收价 |
| quote_time | DATETIME | No | 行情时间 |
| data_source | VARCHAR(20) | No | 数据来源 |
| create_time | DATETIME | No | 创建时间 |
| update_time | DATETIME | No | 更新时间 |

**Unique Index**: `uk_code_source` (`code`, `data_source`)
**Validation**: `price` >= 0; `volume` >= 0; `change_pct` 可为负

---

## Entity: StockDailyQuote (历史K线)

**Table**: `t_stock_daily_quote` (新建)

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| id | INT (PK, AUTO_INCREMENT) | No | 主键 |
| code | VARCHAR(10) | No | 股票代码 |
| trade_date | DATE | No | 交易日期 |
| period | VARCHAR(10) | No | 周期: `daily`, `weekly`, `monthly` |
| open_price | DECIMAL(12, 3) | Yes | 开盘价 |
| high_price | DECIMAL(12, 3) | Yes | 最高价 |
| low_price | DECIMAL(12, 3) | Yes | 最低价 |
| close_price | DECIMAL(12, 3) | Yes | 收盘价 |
| pre_close | DECIMAL(12, 3) | Yes | 前收盘价 |
| volume | DECIMAL(18, 0) | Yes | 成交量 (股) |
| amount | DECIMAL(18, 2) | Yes | 成交额 (元) |
| pct_chg | DECIMAL(8, 2) | Yes | 涨跌幅 (%) |
| data_source | VARCHAR(20) | No | 数据来源 |
| create_time | DATETIME | No | 创建时间 |
| update_time | DATETIME | No | 更新时间 |

**Unique Index**: `uk_code_date_source_period` (`code`, `trade_date`, `data_source`, `period`)
**Validation**: 所有价格字段 >= 0; `volume` >= 0; 日期格式 `YYYY-MM-DD`

---

## Entity: StockFinancial (财务数据)

**Table**: `t_stock_financial` (新建)

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| id | INT (PK, AUTO_INCREMENT) | No | 主键 |
| code | VARCHAR(10) | No | 股票代码 |
| report_date | DATE | No | 报告期 |
| roe | DECIMAL(8, 2) | Yes | ROE (%) |
| net_profit | DECIMAL(18, 2) | Yes | 净利润 (元) |
| revenue | DECIMAL(18, 2) | Yes | 营业收入 (元) |
| eps | DECIMAL(8, 4) | Yes | 每股收益 (元) |
| gross_margin | DECIMAL(8, 2) | Yes | 毛利率 (%) |
| debt_ratio | DECIMAL(8, 2) | Yes | 资产负债率 (%) |
| data_source | VARCHAR(20) | No | 数据来源 |
| create_time | DATETIME | No | 创建时间 |
| update_time | DATETIME | No | 更新时间 |

**Unique Index**: `uk_code_date_source` (`code`, `report_date`, `data_source`)
**Validation**: 报告期必须为季度末日期 (如 `2024-03-31`)

---

## Entity Relationships

```
DataSourceConfig 1:N SyncTask  (一个数据源对应多个同步任务)
Stock 1:N MarketQuote          (一只股票对应多条行情记录，按数据源区分)
Stock 1:N StockDailyQuote      (一只股票对应多条K线记录)
Stock 1:N StockFinancial       (一只股票对应多条财务记录)
```

## Validation Rules Summary

| Rule | Entity | Description |
|------|--------|-------------|
| VR-001 | All | 股票代码必须为 6 位数字（A股），不足补零 |
| VR-002 | All | `data_source` 必须为已配置的数据源类型之一 |
| VR-003 | SyncTask | 同一 `source_type` + `data_type` 组合的 `running` 任务最多 1 个 |
| VR-004 | MarketQuote | 价格和成交量不能为负数 |
| VR-005 | StockDailyQuote | OHLC 价格必须 >= 0, high >= low, high >= open, high >= close |
| VR-006 | DataSourceConfig | `tushare` 类型必须配置 `api_key` |
| VR-007 | StockFinancial | `report_date` 必须为季度末日期 |
