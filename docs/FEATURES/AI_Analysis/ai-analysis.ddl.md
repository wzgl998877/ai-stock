# AI Stock 完整 DDL

> 全量建表脚本，适用于从零建库或完整恢复。
> 包含：模块一（AI 事件分析）+ 模块二扩展（个股多 Agent 分析）+ 模块二数据源集成（004 分支）

---

## 1. 用户表 `t_user`

```sql
CREATE TABLE t_user (
    user_id VARCHAR(32) PRIMARY KEY COMMENT '用户编号',
    user_account VARCHAR(32) NOT NULL COMMENT '登录账号',
    user_name VARCHAR(32) COMMENT '用户名',
    password VARCHAR(128) NOT NULL COMMENT '用户登录密码',
    nick_name VARCHAR(100) COMMENT '昵称',
    icon_url VARCHAR(255) COMMENT '头像地址',
    gender CHAR(1) COMMENT '性别（0=未知,1=男,2=女）',
    mobile VARCHAR(35) COMMENT '手机号码',
    user_type CHAR(1) COMMENT '用户类型（0=普通用户,1=管理员）',
    status CHAR(1) NOT NULL DEFAULT '0' COMMENT '状态（0=正常,1=停用）',
    last_login DATETIME COMMENT '上次登录时间',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',
    create_user VARCHAR(64) COMMENT '记录创建人',
    update_user VARCHAR(64) COMMENT '记录更新人',
    deleted CHAR(1) NOT NULL DEFAULT '0' COMMENT '是否删除（0=未删除,1=已删除）'
) ENGINE=InnoDB COMMENT='用户表';
```

---

## 2. 申万行业字典表 `t_industry`

```sql
CREATE TABLE t_industry (
    industry_code VARCHAR(10) PRIMARY KEY COMMENT '行业代码(如110000)',
    name VARCHAR(30) NOT NULL COMMENT '行业名称(如农林牧渔)',
    level TINYINT NOT NULL COMMENT '行业层级:1=一级,2=二级,3=三级',
    parent_code VARCHAR(10) COMMENT '父级行业代码(一级为NULL)',
    display_order INT NOT NULL DEFAULT 0 COMMENT '显示顺序',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',
    create_user VARCHAR(64) COMMENT '记录创建人',
    update_user VARCHAR(64) COMMENT '记录更新人',
    deleted CHAR(1) NOT NULL DEFAULT '0' COMMENT '是否删除(0=未删除,1=已删除)'
) ENGINE=InnoDB COMMENT='申万行业字典表';

ALTER TABLE t_industry ADD INDEX idx_parent (parent_code);
```

---

## 3. 股票基本信息表 `t_stock`

> 含 004 分支扩展字段（`data_source`、`market_type`）

```sql
CREATE TABLE t_stock (
    stock_code VARCHAR(10) PRIMARY KEY COMMENT '股票代码(如600519)',
    name VARCHAR(50) NOT NULL COMMENT '股票简称(如贵州茅台)',
    full_name VARCHAR(100) COMMENT '股票全称',
    exchange ENUM('SH','SZ','BJ') NOT NULL COMMENT '交易所:SH=上海,SZ=深圳,BJ=北京',
    list_date DATE COMMENT '上市日期',
    is_active BOOLEAN NOT NULL DEFAULT TRUE COMMENT '是否正常交易',
    data_source VARCHAR(20) DEFAULT '' COMMENT '数据来源(tushare/akshare/baostock)',
    market_type VARCHAR(20) COMMENT '市场类型',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',
    create_user VARCHAR(64) COMMENT '记录创建人',
    update_user VARCHAR(64) COMMENT '记录更新人',
    deleted CHAR(1) NOT NULL DEFAULT '0' COMMENT '是否删除(0=未删除,1=已删除)'
) ENGINE=InnoDB COMMENT='股票基本信息表';
```

---

## 4. 股票-行业关联表 `t_stock_industry`

```sql
CREATE TABLE t_stock_industry (
    id VARCHAR(32) PRIMARY KEY COMMENT '主键UUID',
    stock_code VARCHAR(10) NOT NULL COMMENT '股票代码',
    industry_code VARCHAR(10) NOT NULL COMMENT '行业代码',
    is_primary BOOLEAN NOT NULL DEFAULT FALSE COMMENT '是否为主要所属行业',
    classification_source ENUM('official','ai_extracted','user_defined') NOT NULL DEFAULT 'official' COMMENT '行业分类来源',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',
    create_user VARCHAR(64) COMMENT '记录创建人',
    update_user VARCHAR(64) COMMENT '记录更新人',
    deleted CHAR(1) NOT NULL DEFAULT '0' COMMENT '是否删除(0=未删除,1=已删除)'
) ENGINE=InnoDB COMMENT='股票与行业关联表';

ALTER TABLE t_stock_industry ADD UNIQUE KEY uk_stock_industry (stock_code, industry_code);
```

---

## 5. AI 分析文章主表 `t_analysis_article`

> 含 003 分支扩展字段（`article_type`、`analysis_data`）

```sql
CREATE TABLE t_analysis_article (
    article_id VARCHAR(32) PRIMARY KEY COMMENT '文章UUID(32位)',
    title VARCHAR(50) NOT NULL COMMENT 'AI生成标题(≤15字)',
    summary VARCHAR(200) NOT NULL COMMENT 'AI生成摘要(≤80字,2句话结论)',
    content MEDIUMTEXT NOT NULL COMMENT '分析正文(Markdown格式)',
    event_type ENUM('geopolitical','policy','earnings','supply_chain','other') NOT NULL COMMENT '事件类型',
    raw_input VARCHAR(500) NOT NULL COMMENT '用户原始输入(最少10字)',
    chain_table JSON COMMENT '产业链传导表(仅supply_chain类型)',
    article_type VARCHAR(20) NOT NULL DEFAULT 'event' COMMENT '文章类型: event=事件分析, stock_analysis=个股深度分析',
    analysis_data JSON COMMENT '多Agent分析结构化数据',
    status VARCHAR(20) NOT NULL DEFAULT 'completed' COMMENT '分析状态: in_progress=分析中, completed=已完成, stopped=已停止',
    user_id VARCHAR(32) NOT NULL COMMENT '用户编号(关联t_user.user_id)',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',
    create_user VARCHAR(64) COMMENT '记录创建人',
    update_user VARCHAR(64) COMMENT '记录更新人',
    deleted CHAR(1) NOT NULL DEFAULT '0' COMMENT '是否删除(0=未删除,1=已删除)'
) ENGINE=InnoDB COMMENT='AI分析文章主表';

ALTER TABLE t_analysis_article ADD INDEX idx_user_id (user_id);
ALTER TABLE t_analysis_article ADD INDEX idx_article_type (article_type);
```

---

## 6. 文章-行业关联表 `t_article_industry`

```sql
CREATE TABLE t_article_industry (
    id VARCHAR(32) PRIMARY KEY COMMENT '主键UUID',
    article_id VARCHAR(32) NOT NULL COMMENT '文章UUID',
    industry_code VARCHAR(10) NOT NULL COMMENT '行业代码',
    chain_level INT COMMENT '产业链传导层级(仅产业链分析)',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',
    create_user VARCHAR(64) COMMENT '记录创建人',
    update_user VARCHAR(64) COMMENT '记录更新人',
    deleted CHAR(1) NOT NULL DEFAULT '0' COMMENT '是否删除(0=未删除,1=已删除)'
) ENGINE=InnoDB COMMENT='文章与行业关联表';

ALTER TABLE t_article_industry ADD UNIQUE KEY uk_article_industry (article_id, industry_code);
ALTER TABLE t_article_industry ADD INDEX idx_article_id (article_id);
ALTER TABLE t_article_industry ADD INDEX idx_industry_code (industry_code);
```

---

## 7. 文章-股票关联表 `t_article_stock`

```sql
CREATE TABLE t_article_stock (
    id VARCHAR(32) PRIMARY KEY COMMENT '主键UUID',
    article_id VARCHAR(32) NOT NULL COMMENT '文章UUID',
    stock_code VARCHAR(10) NOT NULL COMMENT '股票代码',
    stock_name VARCHAR(50) NOT NULL COMMENT '股票名称(冗余快照)',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',
    create_user VARCHAR(64) COMMENT '记录创建人',
    update_user VARCHAR(64) COMMENT '记录更新人',
    deleted CHAR(1) NOT NULL DEFAULT '0' COMMENT '是否删除(0=未删除,1=已删除)'
) ENGINE=InnoDB COMMENT='文章与股票关联表';

ALTER TABLE t_article_stock ADD UNIQUE KEY uk_article_stock (article_id, stock_code);
ALTER TABLE t_article_stock ADD INDEX idx_article_id (article_id);
ALTER TABLE t_article_stock ADD INDEX idx_stock_code (stock_code);
```

---

## 8. 大事提醒表 `t_event_reminder`

```sql
CREATE TABLE t_event_reminder (
    reminder_id VARCHAR(32) PRIMARY KEY COMMENT '提醒UUID',
    title VARCHAR(100) NOT NULL COMMENT '事件名称',
    event_date DATE NOT NULL COMMENT '事件日期',
    industry_tags JSON COMMENT '关联行业(冗余,便于展示)',
    status ENUM('pending','reminded_3day','reminded_today','archived') NOT NULL DEFAULT 'pending' COMMENT '提醒状态',
    user_id VARCHAR(32) NOT NULL COMMENT '用户编号(关联t_user.user_id)',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',
    create_user VARCHAR(64) COMMENT '记录创建人',
    update_user VARCHAR(64) COMMENT '记录更新人',
    deleted CHAR(1) NOT NULL DEFAULT '0' COMMENT '是否删除(0=未删除,1=已删除)'
) ENGINE=InnoDB COMMENT='大事提醒表';

ALTER TABLE t_event_reminder ADD INDEX idx_user_id (user_id);
```

---

## 9. 对话会话表 `t_chat_session`

> 含 003 分支扩展字段（`session_type`、`config`）

```sql
CREATE TABLE t_chat_session (
    session_id VARCHAR(32) PRIMARY KEY COMMENT '会话UUID',
    user_id VARCHAR(32) NOT NULL COMMENT '用户编号(关联t_user.user_id)',
    title VARCHAR(100) COMMENT '会话标题(自动生成或用户编辑)',
    session_type VARCHAR(20) NOT NULL DEFAULT 'event_analysis' COMMENT '会话类型: event_analysis=事件分析, stock_analysis=个股分析',
    config JSON COMMENT '分析配置参数(股票代码/模式/轮次等)',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',
    create_user VARCHAR(64) COMMENT '记录创建人',
    update_user VARCHAR(64) COMMENT '记录更新人',
    deleted CHAR(1) NOT NULL DEFAULT '0' COMMENT '是否删除(0=未删除,1=已删除)'
) ENGINE=InnoDB COMMENT='对话会话表';

ALTER TABLE t_chat_session ADD INDEX idx_user_id (user_id);
ALTER TABLE t_chat_session ADD INDEX idx_session_type (session_type);
```

---

## 10. 对话消息表 `t_chat_message`

> 含 003 分支扩展字段（`agent_data`）

```sql
CREATE TABLE t_chat_message (
    message_id VARCHAR(32) PRIMARY KEY COMMENT '消息UUID',
    session_id VARCHAR(32) NOT NULL COMMENT '所属会话UUID(关联t_chat_session.session_id)',
    role ENUM('user', 'assistant', 'system') NOT NULL COMMENT '角色:user/assistant/system',
    content MEDIUMTEXT NOT NULL COMMENT '消息内容',
    agent_data JSON COMMENT '多Agent中间数据(Agent状态/进度等)',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间(顺序)',
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',
    create_user VARCHAR(64) COMMENT '记录创建人',
    update_user VARCHAR(64) COMMENT '记录更新人',
    deleted CHAR(1) NOT NULL DEFAULT '0' COMMENT '是否删除(0=未删除,1=已删除)'
) ENGINE=InnoDB COMMENT='对话消息表';

ALTER TABLE t_chat_message ADD INDEX idx_session_id (session_id);
```

---

## 11. 数据源配置表 `t_datasource_config`

> 004 分支新增：存储各数据源的 API 密钥与配置

```sql
CREATE TABLE t_datasource_config (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    source_type VARCHAR(20) NOT NULL UNIQUE COMMENT '数据源类型(tushare/akshare/baostock)',
    api_key VARCHAR(512) COMMENT 'API密钥(Fernet加密)',
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE COMMENT '是否启用',
    priority INT NOT NULL DEFAULT 99 COMMENT '优先级(数字越小优先级越高)',
    config_json JSON COMMENT '扩展配置',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',
    create_user VARCHAR(64) COMMENT '记录创建人',
    update_user VARCHAR(64) COMMENT '记录更新人',
    deleted CHAR(1) NOT NULL DEFAULT '0' COMMENT '是否删除(0=未删除,1=已删除)'
) ENGINE=InnoDB COMMENT='数据源配置表';
```

---

## 12. 同步任务表 `t_sync_task`

> 004 分支新增：记录每次数据同步任务的执行状态与进度

```sql
CREATE TABLE t_sync_task (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    task_id VARCHAR(36) NOT NULL UNIQUE COMMENT '任务UUID',
    source_type VARCHAR(20) NOT NULL COMMENT '数据源类型',
    data_type VARCHAR(30) NOT NULL COMMENT '数据类型(basic_info/quote/daily/financial)',
    status VARCHAR(20) NOT NULL DEFAULT 'pending' COMMENT '任务状态(pending/running/completed/failed)',
    total_count INT COMMENT '总记录数',
    processed_count INT COMMENT '已处理数',
    success_count INT COMMENT '成功数',
    fail_count INT COMMENT '失败数',
    error_message TEXT COMMENT '错误信息',
    start_time DATETIME COMMENT '开始时间',
    end_time DATETIME COMMENT '结束时间',
    duration_ms INT COMMENT '耗时(毫秒)',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间'
) ENGINE=InnoDB COMMENT='同步任务表';

ALTER TABLE t_sync_task ADD INDEX idx_source_status (source_type, status);
ALTER TABLE t_sync_task ADD INDEX idx_create_time (create_time);
```

---

## 13. 实时行情表 `t_market_quote`

> 004 分支新增：存储各数据源的实时行情快照

```sql
CREATE TABLE t_market_quote (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    code VARCHAR(10) NOT NULL COMMENT '股票代码',
    price DECIMAL(12, 3) COMMENT '最新价',
    change_pct DECIMAL(8, 2) COMMENT '涨跌幅(%)',
    change_amount DECIMAL(12, 3) COMMENT '涨跌额',
    volume DECIMAL(18, 0) COMMENT '成交量(股)',
    amount DECIMAL(18, 2) COMMENT '成交额(元)',
    open_price DECIMAL(12, 3) COMMENT '开盘价',
    high_price DECIMAL(12, 3) COMMENT '最高价',
    low_price DECIMAL(12, 3) COMMENT '最低价',
    pre_close DECIMAL(12, 3) COMMENT '昨收价',
    quote_time DATETIME NOT NULL COMMENT '行情时间',
    data_source VARCHAR(20) NOT NULL COMMENT '数据来源',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',
    UNIQUE KEY uk_code_source (code, data_source)
) ENGINE=InnoDB COMMENT='实时行情表';
```

---

## 14. 历史K线表 `t_stock_daily_quote`

> 004 分支新增：存储日/周/月 K 线历史数据

```sql
CREATE TABLE t_stock_daily_quote (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    code VARCHAR(10) NOT NULL COMMENT '股票代码',
    trade_date DATE NOT NULL COMMENT '交易日期',
    period VARCHAR(10) NOT NULL DEFAULT 'daily' COMMENT '周期(daily/weekly/monthly)',
    open_price DECIMAL(12, 3) COMMENT '开盘价',
    high_price DECIMAL(12, 3) COMMENT '最高价',
    low_price DECIMAL(12, 3) COMMENT '最低价',
    close_price DECIMAL(12, 3) COMMENT '收盘价',
    pre_close DECIMAL(12, 3) COMMENT '昨收价',
    volume DECIMAL(18, 0) COMMENT '成交量(股)',
    amount DECIMAL(18, 2) COMMENT '成交额(元)',
    pct_chg DECIMAL(8, 2) COMMENT '涨跌幅(%)',
    data_source VARCHAR(20) NOT NULL COMMENT '数据来源',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',
    UNIQUE KEY uk_code_date_source_period (code, trade_date, data_source, period)
) ENGINE=InnoDB COMMENT='历史K线表';
```

---

## 15. 财务数据表 `t_stock_financial`

> 004 分支新增：存储各数据源的财务报表指标

```sql
CREATE TABLE t_stock_financial (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    code VARCHAR(10) NOT NULL COMMENT '股票代码',
    report_date DATE NOT NULL COMMENT '报告期',
    roe DECIMAL(8, 2) COMMENT '净资产收益率(%)',
    net_profit DECIMAL(18, 2) COMMENT '净利润(元)',
    revenue DECIMAL(18, 2) COMMENT '营业收入(元)',
    eps DECIMAL(8, 4) COMMENT '每股收益',
    gross_margin DECIMAL(8, 2) COMMENT '毛利率(%)',
    debt_ratio DECIMAL(8, 2) COMMENT '资产负债率(%)',
    data_source VARCHAR(20) NOT NULL COMMENT '数据来源',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',
    UNIQUE KEY uk_code_date_source (code, report_date, data_source)
) ENGINE=InnoDB COMMENT='财务数据表';
```

---

## 16. 已有表结构增量迁移（ALTER TABLE）

> 如果已建好基础表，执行以下 ALTER 语句即可补齐新增字段。

### 16.1 分支 `003-stock-analysis` — 个股多 Agent 深度分析

```sql
-- t_analysis_article 新增字段
ALTER TABLE t_analysis_article ADD COLUMN article_type VARCHAR(20) NOT NULL DEFAULT 'event'
    COMMENT '文章类型: event=事件分析, stock_analysis=个股深度分析';
ALTER TABLE t_analysis_article ADD COLUMN analysis_data JSON
    COMMENT '多Agent分析结构化数据';
ALTER TABLE t_analysis_article ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'completed'
    COMMENT '分析状态: in_progress=分析中, completed=已完成, stopped=已停止';
ALTER TABLE t_analysis_article ADD INDEX idx_article_type (article_type);

-- t_chat_session 新增字段
ALTER TABLE t_chat_session ADD COLUMN session_type VARCHAR(20) NOT NULL DEFAULT 'event_analysis'
    COMMENT '会话类型: event_analysis=事件分析, stock_analysis=个股分析';
ALTER TABLE t_chat_session ADD COLUMN config JSON
    COMMENT '分析配置参数(股票代码/模式/轮次等)';
ALTER TABLE t_chat_session ADD INDEX idx_session_type (session_type);

-- t_chat_message 新增字段
ALTER TABLE t_chat_message ADD COLUMN agent_data JSON
    COMMENT '多Agent中间数据(Agent状态/进度等)';
```

### 16.2 分支 `004-data-source-integration` — 多数据源集成

```sql
-- t_stock 新增字段
ALTER TABLE t_stock ADD COLUMN data_source VARCHAR(20) DEFAULT ''
    COMMENT '数据来源(tushare/akshare/baostock)';
ALTER TABLE t_stock ADD COLUMN market_type VARCHAR(20)
    COMMENT '市场类型';
```

### 16.3 新表创建（004 分支新增 5 张表）

```sql
-- 数据源配置表
CREATE TABLE t_datasource_config (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    source_type VARCHAR(20) NOT NULL UNIQUE COMMENT '数据源类型(tushare/akshare/baostock)',
    api_key VARCHAR(512) COMMENT 'API密钥(Fernet加密)',
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE COMMENT '是否启用',
    priority INT NOT NULL DEFAULT 99 COMMENT '优先级(数字越小优先级越高)',
    config_json JSON COMMENT '扩展配置',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',
    create_user VARCHAR(64) COMMENT '记录创建人',
    update_user VARCHAR(64) COMMENT '记录更新人',
    deleted CHAR(1) NOT NULL DEFAULT '0' COMMENT '是否删除(0=未删除,1=已删除)'
) ENGINE=InnoDB COMMENT='数据源配置表';

-- 同步任务表
CREATE TABLE t_sync_task (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    task_id VARCHAR(36) NOT NULL UNIQUE COMMENT '任务UUID',
    source_type VARCHAR(20) NOT NULL COMMENT '数据源类型',
    data_type VARCHAR(30) NOT NULL COMMENT '数据类型(basic_info/quote/daily/financial)',
    status VARCHAR(20) NOT NULL DEFAULT 'pending' COMMENT '任务状态(pending/running/completed/failed)',
    total_count INT COMMENT '总记录数',
    processed_count INT COMMENT '已处理数',
    success_count INT COMMENT '成功数',
    fail_count INT COMMENT '失败数',
    error_message TEXT COMMENT '错误信息',
    start_time DATETIME COMMENT '开始时间',
    end_time DATETIME COMMENT '结束时间',
    duration_ms INT COMMENT '耗时(毫秒)',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间'
) ENGINE=InnoDB COMMENT='同步任务表';
ALTER TABLE t_sync_task ADD INDEX idx_source_status (source_type, status);
ALTER TABLE t_sync_task ADD INDEX idx_create_time (create_time);

-- 实时行情表
CREATE TABLE t_market_quote (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    code VARCHAR(10) NOT NULL COMMENT '股票代码',
    price DECIMAL(12, 3) COMMENT '最新价',
    change_pct DECIMAL(8, 2) COMMENT '涨跌幅(%)',
    change_amount DECIMAL(12, 3) COMMENT '涨跌额',
    volume DECIMAL(18, 0) COMMENT '成交量(股)',
    amount DECIMAL(18, 2) COMMENT '成交额(元)',
    open_price DECIMAL(12, 3) COMMENT '开盘价',
    high_price DECIMAL(12, 3) COMMENT '最高价',
    low_price DECIMAL(12, 3) COMMENT '最低价',
    pre_close DECIMAL(12, 3) COMMENT '昨收价',
    quote_time DATETIME NOT NULL COMMENT '行情时间',
    data_source VARCHAR(20) NOT NULL COMMENT '数据来源',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',
    UNIQUE KEY uk_code_source (code, data_source)
) ENGINE=InnoDB COMMENT='实时行情表';

-- 历史K线表
CREATE TABLE t_stock_daily_quote (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    code VARCHAR(10) NOT NULL COMMENT '股票代码',
    trade_date DATE NOT NULL COMMENT '交易日期',
    period VARCHAR(10) NOT NULL DEFAULT 'daily' COMMENT '周期(daily/weekly/monthly)',
    open_price DECIMAL(12, 3) COMMENT '开盘价',
    high_price DECIMAL(12, 3) COMMENT '最高价',
    low_price DECIMAL(12, 3) COMMENT '最低价',
    close_price DECIMAL(12, 3) COMMENT '收盘价',
    pre_close DECIMAL(12, 3) COMMENT '昨收价',
    volume DECIMAL(18, 0) COMMENT '成交量(股)',
    amount DECIMAL(18, 2) COMMENT '成交额(元)',
    pct_chg DECIMAL(8, 2) COMMENT '涨跌幅(%)',
    data_source VARCHAR(20) NOT NULL COMMENT '数据来源',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',
    UNIQUE KEY uk_code_date_source_period (code, trade_date, data_source, period)
) ENGINE=InnoDB COMMENT='历史K线表';

-- 财务数据表
CREATE TABLE t_stock_financial (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    code VARCHAR(10) NOT NULL COMMENT '股票代码',
    report_date DATE NOT NULL COMMENT '报告期',
    roe DECIMAL(8, 2) COMMENT '净资产收益率(%)',
    net_profit DECIMAL(18, 2) COMMENT '净利润(元)',
    revenue DECIMAL(18, 2) COMMENT '营业收入(元)',
    eps DECIMAL(8, 4) COMMENT '每股收益',
    gross_margin DECIMAL(8, 2) COMMENT '毛利率(%)',
    debt_ratio DECIMAL(8, 2) COMMENT '资产负债率(%)',
    data_source VARCHAR(20) NOT NULL COMMENT '数据来源',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',
    UNIQUE KEY uk_code_date_source (code, report_date, data_source)
) ENGINE=InnoDB COMMENT='财务数据表';
```

---

## 16. 个股分析主表 `t_stock_analysis`

```sql
CREATE TABLE t_stock_analysis (
    analysis_id VARCHAR(32) PRIMARY KEY COMMENT '分析UUID',
    stock_code VARCHAR(10) NOT NULL COMMENT '股票代码',
    stock_name VARCHAR(50) NOT NULL COMMENT '股票简称',
    analysis_mode VARCHAR(10) NOT NULL DEFAULT 'full' COMMENT '分析模式: quick/full',
    status VARCHAR(20) NOT NULL DEFAULT 'pending' COMMENT '状态: pending/in_progress/completed/stopped/failed',
    current_phase VARCHAR(20) NOT NULL DEFAULT 'analysts' COMMENT '当前阶段: analysts/debate/trader/risk/done',
    title VARCHAR(100) NOT NULL DEFAULT '' COMMENT 'AI生成标题',
    summary VARCHAR(500) NOT NULL DEFAULT '' COMMENT 'AI生成摘要',
    full_content MEDIUMTEXT COMMENT '完整报告Markdown',
    decision_action VARCHAR(20) COMMENT '决策: 买入/持有/卖出',
    target_price DECIMAL(12,3) COMMENT '目标价',
    stop_loss_price DECIMAL(12,3) COMMENT '止损价',
    confidence DECIMAL(5,4) COMMENT '置信度 0-1',
    risk_score DECIMAL(5,4) COMMENT '风险评分 0-1',
    reasoning TEXT COMMENT '决策理由',
    industries JSON COMMENT '关联行业列表',
    data_source VARCHAR(20) NOT NULL DEFAULT '' COMMENT '数据来源',
    article_id VARCHAR(32) COMMENT '同步到知识库后的article_id',
    session_id VARCHAR(32) COMMENT '关联会话ID',
    user_id VARCHAR(32) NOT NULL COMMENT '用户ID（逻辑关联，无外键约束）',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',
    create_user VARCHAR(64) COMMENT '记录创建人',
    update_user VARCHAR(64) COMMENT '记录更新人',
    deleted CHAR(1) NOT NULL DEFAULT '0' COMMENT '是否删除(0=未删除,1=已删除)'
) ENGINE=InnoDB COMMENT='个股分析主表';

CREATE INDEX idx_sa_stock_code ON t_stock_analysis(stock_code);
CREATE INDEX idx_sa_status ON t_stock_analysis(status);
CREATE INDEX idx_sa_user_id ON t_stock_analysis(user_id);
CREATE INDEX idx_sa_create_time ON t_stock_analysis(create_time);
CREATE INDEX idx_sa_article_id ON t_stock_analysis(article_id);
```

---

## 17. 个股分析详情表 `t_stock_analysis_detail`

```sql
CREATE TABLE t_stock_analysis_detail (
    detail_id VARCHAR(32) PRIMARY KEY COMMENT '详情UUID',
    analysis_id VARCHAR(32) NOT NULL COMMENT '关联主表',
    agent_name VARCHAR(50) NOT NULL COMMENT 'Agent名称: 如market_analyst',
    phase VARCHAR(20) NOT NULL COMMENT '阶段: analysts/debate/trader/risk',
    status VARCHAR(20) NOT NULL DEFAULT 'pending' COMMENT '状态: pending/running/done/failed',
    summary VARCHAR(500) COMMENT 'Agent摘要',
    full_report MEDIUMTEXT COMMENT 'Agent完整报告',
    thinking_steps JSON COMMENT '思考步骤',
    debate_data JSON COMMENT '辩论数据',
    error_message TEXT COMMENT '错误信息',
    completed_at DATETIME COMMENT '完成时间',
    display_order INT NOT NULL DEFAULT 0 COMMENT '显示顺序',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',
    create_user VARCHAR(64) COMMENT '记录创建人',
    update_user VARCHAR(64) COMMENT '记录更新人',
    deleted CHAR(1) NOT NULL DEFAULT '0' COMMENT '是否删除(0=未删除,1=已删除)',
    FOREIGN KEY (analysis_id) REFERENCES t_stock_analysis(analysis_id) ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='个股分析详情表';

CREATE INDEX idx_sad_analysis_id ON t_stock_analysis_detail(analysis_id);
CREATE INDEX idx_sad_agent_name ON t_stock_analysis_detail(agent_name);
CREATE INDEX idx_sad_phase ON t_stock_analysis_detail(phase);
CREATE INDEX idx_sad_status ON t_stock_analysis_detail(status);
```

---

## 迁移脚本 — 005 分支（新增 t_stock_analysis + t_stock_analysis_detail）

```sql
-- 见 Alembic 迁移: c3d4e5f6a7b8
-- 存量数据迁移: python -m scripts.migrate_analysis_data
```

### 005 分支增量 — 增加 stop_loss_price 字段

```sql
-- 见 Alembic 迁移: d4e5f6a7b8c9
ALTER TABLE t_stock_analysis ADD COLUMN stop_loss_price DECIMAL(12,3) NULL
    COMMENT '止损价' AFTER target_price;
```

### 005 分支增量 — content 列扩容为 MEDIUMTEXT

> 深度分析报告内容可能超过 TEXT（65KB）上限，需扩容为 MEDIUMTEXT（16MB）。

```sql
-- t_analysis_article.content: 分析正文
ALTER TABLE t_analysis_article MODIFY COLUMN content MEDIUMTEXT NOT NULL
    COMMENT '分析正文(Markdown格式)';

-- t_chat_message.content: 对话消息内容
ALTER TABLE t_chat_message MODIFY COLUMN content MEDIUMTEXT NOT NULL
    COMMENT '消息内容';

-- t_stock_analysis.full_content: 完整报告
ALTER TABLE t_stock_analysis MODIFY COLUMN full_content MEDIUMTEXT
    COMMENT '完整报告Markdown';

-- t_stock_analysis_detail.full_report: Agent 完整报告
ALTER TABLE t_stock_analysis_detail MODIFY COLUMN full_report MEDIUMTEXT
    COMMENT 'Agent完整报告';
```

---

## 表清单总览

| # | 表名 | 说明 | 来源 |
|---|------|------|------|
| 1 | `t_user` | 用户表 | 基础 |
| 2 | `t_industry` | 申万行业字典 | 基础 |
| 3 | `t_stock` | 股票基本信息 | 基础 + 004 |
| 4 | `t_stock_industry` | 股票-行业关联 | 基础 |
| 5 | `t_analysis_article` | AI 分析文章 | 基础 + 003 + 005 |
| 6 | `t_article_industry` | 文章-行业关联 | 基础 |
| 7 | `t_article_stock` | 文章-股票关联 | 基础 |
| 8 | `t_event_reminder` | 大事提醒 | 基础 |
| 9 | `t_chat_session` | 对话会话 | 基础 + 003 |
| 10 | `t_chat_message` | 对话消息 | 基础 + 003 |
| 11 | `t_datasource_config` | 数据源配置 | **004 新增** |
| 12 | `t_sync_task` | 同步任务 | **004 新增** |
| 13 | `t_market_quote` | 实时行情 | **004 新增** |
| 14 | `t_stock_daily_quote` | 历史K线 | **004 新增** |
| 15 | `t_stock_financial` | 财务数据 | **004 新增** |
| 16 | `t_stock_analysis` | 个股分析主表 | **005 新增** |
| 17 | `t_stock_analysis_detail` | 个股分析详情表 | **005 新增** |
