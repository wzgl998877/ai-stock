# 模块二：行情数据展示 DDL

> 分支 `006-stock-detail-kline` 新增及修改的数据库表结构。
> Alembic 迁移脚本: `e5f6a7b8c9d0_add_market_data_module2_tables.py`

---

## 1. 新增表

### 1.1 自选股分组表 `t_watchlist_group`

```sql
CREATE TABLE t_watchlist_group (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    user_id VARCHAR(64) NOT NULL COMMENT '用户ID（当前固定 default）',
    name VARCHAR(10) NOT NULL COMMENT '分组名称（限10字）',
    display_order INT NOT NULL DEFAULT 0 COMMENT '排序序号',
    is_default BOOLEAN NOT NULL DEFAULT FALSE COMMENT '是否默认分组',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB COMMENT='自选股分组表';

ALTER TABLE t_watchlist_group ADD INDEX idx_wg_user_id (user_id);
```

---

### 1.2 自选股条目表 `t_watchlist_item`

```sql
CREATE TABLE t_watchlist_item (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    group_id INT NOT NULL COMMENT '所属分组ID',
    stock_code VARCHAR(10) NOT NULL COMMENT '股票代码',
    stock_name VARCHAR(50) NOT NULL COMMENT '股票名称（冗余快照）',
    add_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '加入时间',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'
) ENGINE=InnoDB COMMENT='自选股条目表';

ALTER TABLE t_watchlist_item ADD UNIQUE KEY uk_group_stock (group_id, stock_code);
ALTER TABLE t_watchlist_item ADD INDEX idx_wi_group_id (group_id);
ALTER TABLE t_watchlist_item ADD INDEX idx_wi_stock_code (stock_code);
```

---

### 1.3 技术指标表 `t_stock_indicator`

```sql
CREATE TABLE t_stock_indicator (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    stock_code VARCHAR(10) NOT NULL COMMENT '股票代码',
    trade_date DATE NOT NULL COMMENT '交易日期',
    period VARCHAR(10) NOT NULL DEFAULT 'daily' COMMENT '周期（daily/weekly/monthly）',
    macd_dif DECIMAL(12, 4) COMMENT 'MACD DIF 值',
    macd_dea DECIMAL(12, 4) COMMENT 'MACD DEA 值',
    macd_bar DECIMAL(12, 4) COMMENT 'MACD 柱状值',
    kdj_k DECIMAL(8, 4) COMMENT 'KDJ K 值',
    kdj_d DECIMAL(8, 4) COMMENT 'KDJ D 值',
    kdj_j DECIMAL(8, 4) COMMENT 'KDJ J 值',
    ma5 DECIMAL(12, 3) COMMENT '5日均线',
    ma10 DECIMAL(12, 3) COMMENT '10日均线',
    ma20 DECIMAL(12, 3) COMMENT '20日均线',
    data_source VARCHAR(20) NOT NULL COMMENT '数据来源',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB COMMENT='技术指标表（MACD/KDJ/MA）';

ALTER TABLE t_stock_indicator ADD UNIQUE KEY uk_stock_indicator (stock_code, trade_date, period);
ALTER TABLE t_stock_indicator ADD INDEX idx_si_stock_date (stock_code, trade_date);
```

---

## 2. 已有表增量迁移（ALTER TABLE）

### 2.1 `t_stock` — 新增行业与市值字段

```sql
ALTER TABLE t_stock ADD COLUMN industry_code VARCHAR(10) COMMENT '行业代码（申万一级）';
ALTER TABLE t_stock ADD COLUMN industry_name VARCHAR(50) COMMENT '行业名称';
ALTER TABLE t_stock ADD COLUMN total_market_cap DECIMAL(18, 2) COMMENT '总市值（元）';
ALTER TABLE t_stock ADD COLUMN float_market_cap DECIMAL(18, 2) COMMENT '流通市值（元）';
```

### 2.2 `t_market_quote` — 新增估值字段

```sql
ALTER TABLE t_market_quote ADD COLUMN pe_ttm DECIMAL(10, 2) COMMENT '市盈率 TTM';
ALTER TABLE t_market_quote ADD COLUMN pb DECIMAL(10, 2) COMMENT '市净率';
```

---

## 3. 复用的已有表

以下表在 006 分支中直接复用，未做结构变更：

| 表名 | 说明 | 复用方式 |
|------|------|----------|
| `t_industry` | 申万行业字典（31个一级行业） | 行业导航 + 行业对比 |
| `t_stock_industry` | 股票-行业关联 | 按行业查股票列表 |
| `t_article_stock` | 文章-股票关联 | 个股详情页关联分析文章 |
| `t_stock_daily_quote` | 历史K线 | K线图数据源 |
| `t_stock_financial` | 财务数据 | 财务指标展示 |
| `t_market_quote` | 实时行情 | 价格卡 + 行情展示 |

---

## 4. 表清单总览

| # | 表名 | 说明 | 变更类型 |
|---|------|------|----------|
| 1 | `t_watchlist_group` | 自选股分组 | **006 新增** |
| 2 | `t_watchlist_item` | 自选股条目 | **006 新增** |
| 3 | `t_stock_indicator` | 技术指标（MACD/KDJ/MA） | **006 新增** |
| 4 | `t_stock` | 股票基本信息 | **006 扩展** +4 字段 |
| 5 | `t_market_quote` | 实时行情 | **006 扩展** +2 字段 |
| 6 | `t_industry` | 申万行业字典 | 复用 |
| 7 | `t_stock_industry` | 股票-行业关联 | 复用 |
| 8 | `t_article_stock` | 文章-股票关联 | 复用 |
| 9 | `t_stock_daily_quote` | 历史K线 | 复用 |
| 10 | `t_stock_financial` | 财务数据 | 复用 |
