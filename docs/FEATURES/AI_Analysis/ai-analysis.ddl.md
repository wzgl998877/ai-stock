

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

```sql
CREATE TABLE t_stock (
    stock_code VARCHAR(10) PRIMARY KEY COMMENT '股票代码(如600519)',
    name VARCHAR(50) NOT NULL COMMENT '股票简称(如贵州茅台)',
    full_name VARCHAR(100) COMMENT '股票全称',
    exchange ENUM('SH','SZ','BJ') NOT NULL COMMENT '交易所:SH=上海,SZ=深圳,BJ=北京',
    list_date DATE COMMENT '上市日期',
    is_active BOOLEAN NOT NULL DEFAULT TRUE COMMENT '是否正常交易',
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

-- 唯一约束：避免重复关联
ALTER TABLE t_stock_industry ADD UNIQUE KEY uk_stock_industry (stock_code, industry_code);
```

---

## 5. AI 分析文章主表 `t_analysis_article`

```sql
CREATE TABLE t_analysis_article (
    article_id VARCHAR(32) PRIMARY KEY COMMENT '文章UUID(32位)',
    title VARCHAR(50) NOT NULL COMMENT 'AI生成标题(≤15字)',
    summary VARCHAR(200) NOT NULL COMMENT 'AI生成摘要(≤80字,2句话结论)',
    content TEXT NOT NULL COMMENT '分析正文(Markdown格式)',
    event_type ENUM('geopolitical','policy','earnings','supply_chain','other') NOT NULL COMMENT '事件类型',
    raw_input VARCHAR(500) NOT NULL COMMENT '用户原始输入(最少10字)',
    chain_table JSON COMMENT '产业链传导表(仅supply_chain类型)',
    user_id VARCHAR(32) NOT NULL COMMENT '用户编号(关联t_user.user_id)',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',
    create_user VARCHAR(64) COMMENT '记录创建人',
    update_user VARCHAR(64) COMMENT '记录更新人',
    deleted CHAR(1) NOT NULL DEFAULT '0' COMMENT '是否删除(0=未删除,1=已删除)'
) ENGINE=InnoDB COMMENT='AI分析文章主表';

-- 只加 user_id 索引（关联字段）
ALTER TABLE t_analysis_article ADD INDEX idx_user_id (user_id);
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

-- 唯一约束：避免重复关联
ALTER TABLE t_article_industry ADD UNIQUE KEY uk_article_industry (article_id, industry_code);
-- 关联字段索引
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

-- 唯一约束：避免重复关联
ALTER TABLE t_article_stock ADD UNIQUE KEY uk_article_stock (article_id, stock_code);
-- 关联字段索引
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

-- 只加 user_id 索引（关联字段）
ALTER TABLE t_event_reminder ADD INDEX idx_user_id (user_id);
```

---

## 9. 对话会话表 `t_chat_session`

```sql
CREATE TABLE t_chat_session (
    session_id VARCHAR(32) PRIMARY KEY COMMENT '会话UUID',
    user_id VARCHAR(32) NOT NULL COMMENT '用户编号(关联t_user.user_id)',
    title VARCHAR(100) COMMENT '会话标题(自动生成或用户编辑)',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',
    create_user VARCHAR(64) COMMENT '记录创建人',
    update_user VARCHAR(64) COMMENT '记录更新人',
    deleted CHAR(1) NOT NULL DEFAULT '0' COMMENT '是否删除(0=未删除,1=已删除)'
) ENGINE=InnoDB COMMENT='对话会话表';

-- 只加 user_id 索引（关联字段）
ALTER TABLE t_chat_session ADD INDEX idx_user_id (user_id);
```

---

## 10. 对话消息表 `t_chat_message`

```sql
CREATE TABLE t_chat_message (
    message_id VARCHAR(32) PRIMARY KEY COMMENT '消息UUID',
    session_id VARCHAR(32) NOT NULL COMMENT '所属会话UUID(关联t_chat_session.session_id)',
    role ENUM('user', 'assistant', 'system') NOT NULL COMMENT '角色:user/assistant/system',
    content TEXT NOT NULL COMMENT '消息内容',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间(顺序)',
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',
    create_user VARCHAR(64) COMMENT '记录创建人',
    update_user VARCHAR(64) COMMENT '记录更新人',
    deleted CHAR(1) NOT NULL DEFAULT '0' COMMENT '是否删除(0=未删除,1=已删除)'
) ENGINE=InnoDB COMMENT='对话消息表';

-- 只加 session_id 索引（关联字段）
ALTER TABLE t_chat_message ADD INDEX idx_session_id (session_id);
```

---

## 11. 个股多Agent深度分析 — 字段扩展迁移

> 功能分支: `003-stock-analysis` | 变更方式: ALTER 新增字段（向后兼容，现有数据不受影响）

### 11.1 `t_analysis_article` 新增字段

```sql
-- 区分文章类型: event=事件分析(原有), stock_analysis=个股深度分析(新增)
ALTER TABLE t_analysis_article ADD COLUMN article_type VARCHAR(20) NOT NULL DEFAULT 'event'
    COMMENT '文章类型: event=事件分析, stock_analysis=个股深度分析';

-- 存储多Agent分析的结构化数据(各Agent报告/辩论记录/最终决策等)
ALTER TABLE t_analysis_article ADD COLUMN analysis_data JSON
    COMMENT '多Agent分析结构化数据';

-- 索引: 按文章类型查询(如"查所有个股分析文章")
ALTER TABLE t_analysis_article ADD INDEX idx_article_type (article_type);
```

### 11.2 `t_chat_session` 新增字段

```sql
-- 区分会话类型: event_analysis=事件分析(原有), stock_analysis=个股分析(新增)
ALTER TABLE t_chat_session ADD COLUMN session_type VARCHAR(20) NOT NULL DEFAULT 'event_analysis'
    COMMENT '会话类型: event_analysis=事件分析, stock_analysis=个股分析';

-- 存储分析配置参数(股票代码/分析模式/辩论轮次等)
ALTER TABLE t_chat_session ADD COLUMN config JSON
    COMMENT '分析配置参数(股票代码/模式/轮次等)';

-- 索引: 按会话类型查询
ALTER TABLE t_chat_session ADD INDEX idx_session_type (session_type);
```

### 11.3 `t_chat_message` 新增字段

```sql
-- 存储多Agent中间数据(当前哪个Agent在工作/各Agent状态等)
ALTER TABLE t_chat_message ADD COLUMN agent_data JSON
    COMMENT '多Agent中间数据(Agent状态/进度等)';
```
