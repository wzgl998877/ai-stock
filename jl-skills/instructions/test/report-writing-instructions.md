# 报告写入指令 (Report Writing Instructions)

## ⚠️ 执行规则 (EXECUTION RULES)

```
🛑 CRITICAL: 
- 每个步骤输出后 MUST STOP
- 等待用户回复后才能继续
- 一次回复只输出一个步骤的内容
- 违反此规则将导致流程失败
```

此文档指导 Agent 执行场景测试生成的**步骤 4: 报告写入**。

> [!IMPORTANT]
> **目标**: 使用模板整合所有内容，写入完整的测试报告。
> **原则**: 参考 `jl-skills/templates/JL-Template-Scenario-Test-Case.md` 的格式。

---

## 步骤 4.1: 报告整合准备

**你必须输出以下内容，然后停止**:

**回顾内容**:
1. 步骤1: 场景概览表
2. 步骤2: 业务逻辑与流程（含Mermaid图）
3. 步骤3: cURL 和 SQL 脚本（已生成，保留在内存中）

**输出格式**:

````markdown
## 步骤 4: 报告写入

📊 **进度**: [4/5] 报告写入
[████████████████░░░░] 80%

| ✅ 已完成 | 🔄 进行中 | ⏳ 待完成 |
|:----------|:----------|:----------|
| 1.场景概览 | 4.报告写入 | 5.Python测试脚本 |
| 2.流程介绍 | | |
| 3.脚本生成 | | |

---

### ⚠️ 报告写入说明

**整合内容**:
- ✅ 步骤1: 测试场景概览表
- ✅ 步骤2: 业务逻辑与流程（含Mermaid时序图）
- ✅ 步骤3: cURL 和 SQL 脚本（直接写入报告）

**报告模板**: `jl-skills/templates/JL-Template-Scenario-Test-Case.md`

**报告结构**:
1. 测试场景概览 (Test Scenarios)
2. 业务逻辑与流程 (Logic & Flow)
3. 执行脚本集 (Execution Scripts)
   - A. 接口请求 (cURL)
   - B. 数据准备与校验 (SQL)
   - C. 自动化验证 (Python) - 将在步骤5生成

**报告文件**: `jl-skills/generated/test/{date}/Scenario_Test_Case.md`

---

📋 **确认检查点**

是否开始写入报告？

- 回复 **确认** → 立即写入报告文件
- 回复 **调整** → 我将修改报告内容

**请确认：** 是否开始写入报告？
````

**🛑 STOP HERE - DO NOT OUTPUT STEP 4.2 UNTIL USER CONFIRMS**

⚠️ **重要**: 用户未回复"确认"前，禁止执行任何后续步骤，禁止输出步骤4.2的内容。

---

## 步骤 4.2: 报告写入

**你必须输出以下内容，然后停止**:

**整合规则**:
1. **使用模板**: `jl-skills/templates/JL-Template-Scenario-Test-Case.md`
2. **填充内容**: 场景概览表、业务逻辑与流程、Mermaid 时序图、cURL 脚本、SQL 脚本
3. **添加元数据**: 日期时间戳、相关模块/功能
4. **脚本位置**: cURL 和 SQL 脚本直接写入报告的"执行脚本集"部分

**执行规则**:
- 直接写入报告文件
- 使用模板格式

**输出格式**:

````markdown
### ✅ 报告已写入

**报告文件**: `jl-skills/generated/test/{date}/Scenario_Test_Case.md`

**报告内容**:
- ✅ 测试场景概览表（X 个场景）
- ✅ 业务逻辑与流程说明
- ✅ 正常流程时序图
- ✅ 异常流程时序图
- ✅ cURL 脚本（完整内容）
- ✅ SQL 脚本（完整内容）

**报告结构**:
1. 测试场景概览 (Test Scenarios)
2. 业务逻辑与流程 (Logic & Flow)
3. 执行脚本集 (Execution Scripts)
   - A. 接口请求 (cURL)
   - B. 数据准备与校验 (SQL)
   - C. 自动化验证 (Python) - 将在步骤5生成

---

📋 **确认检查点**

报告写入是否完成？

- 回复 **确认** → 进入Python测试脚本生成
- 回复 **调整报告: [具体说明]** → 我将修改报告

**请确认：** 报告写入是否完成？
````

**🛑 STOP HERE - DO NOT OUTPUT STEP 4.3 UNTIL USER CONFIRMS**

⚠️ **重要**: 用户未回复"确认"前，禁止执行任何后续步骤，禁止输出步骤4.3的内容。