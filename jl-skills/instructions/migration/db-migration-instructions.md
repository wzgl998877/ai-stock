# 数据库迁移指令 (DB Migration Instructions)

## ⚠️ 执行规则 (EXECUTION RULES)

```
🛑 CRITICAL: 
- 每个步骤输出后 MUST STOP
- 等待用户回复后才能继续
- 一次回复只输出一个步骤的内容
- 违反此规则将导致流程失败
```

此文档指导 Agent 执行**数据库迁移（阶段 3）**。

> [!IMPORTANT]
> **目标**: 完成 Schema 转换和数据迁移脚本。

---

## 步骤 1: Schema 转换

**你必须输出以下内容，然后停止**:

### 1.1 提取DDL

**提取内容**: 提取旧库的 DDL

### 1.2 转换Schema

**转换内容**:
1. **数据类型转换**: 根据目标数据库（如 PostgreSQL），转换数据类型
2. **优化索引**: 优化索引结构
3. **规范命名**: 规范命名（snake_case）

### 1.3 输出Schema转换

**输出格式**:

````markdown
## 步骤 1: Schema 转换

📊 **进度**: [1/3] 数据库迁移
[███████░░░░░░░░░░░░░] 33%

| ✅ 已完成 | 🔄 进行中 | ⏳ 待完成 |
|:----------|:----------|:----------|
| | 1.Schema转换 | 2.数据迁移脚本 |
| | | 3.交付 |

---

### 新 DDL 预览

**目标数据库**: PostgreSQL

**主要变更**:
- 数据类型转换: `VARCHAR` → `TEXT`
- 索引优化: 添加复合索引
- 命名规范: `camelCase` → `snake_case`

**示例DDL**:
```sql
CREATE TABLE orders (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    status VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_status (user_id, status)
);
```

---

📋 **确认检查点**

Schema 转换是否准确？

- 回复 **确认** → 进入数据迁移脚本生成
- 回复 **调整Schema: [内容]** → 我将调整
- 回复 **调整命名: [内容]** → 我将调整

**请确认：** Schema 转换是否正确？
````

**🛑 STOP HERE - 必须等待用户确认后才能继续**

⚠️ **重要**: 用户未回复"确认"前，禁止执行任何后续步骤。

---

## 步骤 2: 数据迁移脚本

### 2.1 生成迁移脚本

**生成内容**:
1. **ETL脚本**: 编写 ETL 脚本或 SQL 转换脚本
2. **数据清洗**: 处理枚举转换、空值处理

### 2.2 编写校验逻辑

**校验内容**: 编写数据校验 SQL（Count 校验、Sum 校验）

### 2.3 输出迁移脚本

**输出格式**:

````markdown
## 步骤 2: 数据迁移脚本

📊 **进度**: [2/3] 数据库迁移
[█████████████░░░░░░░] 67%

| ✅ 已完成 | 🔄 进行中 | ⏳ 待完成 |
|:----------|:----------|:----------|
| 1.Schema转换 | 2.数据迁移脚本 | 3.交付 |

---

### 数据迁移脚本预览

**脚本文件**: `db/migration/migrate_data.sql`

**脚本内容**:
```sql
-- 1. 数据转换
INSERT INTO new_orders (id, user_id, status, created_at)
SELECT id, user_id, status, created_at
FROM old_orders;

-- 2. 枚举值转换
UPDATE new_orders 
SET status = CASE 
    WHEN status = 'CREATED' THEN 'created'
    WHEN status = 'PAID' THEN 'paid'
    ELSE 'unknown'
END;

-- 3. 数据校验
SELECT COUNT(*) as total_count FROM new_orders;
SELECT SUM(amount) as total_amount FROM new_orders;
```

---

📋 **确认检查点**

数据迁移脚本是否完整？

- 回复 **确认** → 进入交付
- 回复 **调整脚本: [内容]** → 我将调整

**请确认：** 数据迁移脚本是否完整？
````

**🛑 STOP HERE - DO NOT OUTPUT STEP 3 UNTIL USER CONFIRMS**

⚠️ **重要**: 用户未回复"确认"前，禁止执行任何后续步骤，禁止输出步骤3的内容。

---

## 步骤 3: 交付

**你必须输出以下内容，然后停止**:

### 3.1 保存文件

**保存内容**:
1. **DDL**: 保存到 `db/schema.sql`
2. **迁移脚本**: 保存到 `db/migration/`

### 3.2 输出交付结果

**输出格式**:

````markdown
## 步骤 3: 交付

📊 **进度**: [3/3] 数据库迁移
[████████████████████] 100%

| ✅ 已完成 | 🔄 进行中 | ⏳ 待完成 |
|:----------|:----------|:----------|
| 1.Schema转换 | 3.交付 | |
| 2.数据迁移脚本 | | |

---

### ✅ 文件已保存

**保存位置**:
- `db/schema.sql` - 新数据库Schema
- `db/migration/migrate_data.sql` - 数据迁移脚本
- `db/migration/validate_data.sql` - 数据校验脚本

---

📋 **确认检查点**

交付是否完成？

- 回复 **确认** → 进入下一阶段
- 回复 **调整: [内容]** → 我将调整

**请确认：** 交付是否完成？
````

**🛑 STOP HERE - 必须等待用户确认后才能继续**

⚠️ **重要**: 用户未回复"确认"前，禁止执行任何后续步骤。

---

## 阶段 3 完成: 准备进入分层重构

**触发条件**: 用户确认步骤3后

**输出格式**:

````markdown
---

## ✅ 阶段 3 完成

| ✅ 已完成 | 🔄 即将开始 |
|:----------|:------------|
| 阶段1: 范围分析 | 阶段4: 分层重构 |
| 阶段2: 黄金测试 | |
| 阶段3: 数据迁移 | |

**数据迁移已完成**:
- ✅ Schema 已转换
- ✅ 数据迁移脚本已生成
- ✅ 文件已保存

---

🛑 **下一步**

是否进入阶段4: 分层重构？

请回复：
- **继续** → 进入阶段4: 分层重构
- **结束** → 完成当前流程
````

**🛑 STOP HERE - 等待用户确认进入下一阶段**