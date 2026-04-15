# Python 端到端测试脚本指令 (Python E2E Test Instructions)

## ⚠️ 执行规则 (EXECUTION RULES)

```
🛑 CRITICAL: 
- 每个步骤输出后 MUST STOP
- 等待用户回复后才能继续
- 一次回复只输出一个步骤的内容
- 违反此规则将导致流程失败
```

此文档指导 Agent 执行场景测试生成的**步骤 5: Python 端到端测试脚本**。

> [!IMPORTANT]
> **目标**: 生成 Python 端到端测试脚本，包含所有场景的测试用例。
> **原则**: 参考 `jl-skills/templates/JL-Template-Scenario-Test-Case.md` 的格式。

---

## 步骤 5.1: Python 脚本生成准备

**你必须输出以下内容，然后停止**:

**确认内容**:
1. 回顾步骤1的场景概览表
2. 确认需要为哪些场景生成 Python 测试脚本

**输出格式**:

````markdown
## 步骤 5: Python 端到端测试脚本

📊 **进度**: [5/5] Python测试脚本生成
[████████████████████] 100%

| ✅ 已完成 | 🔄 进行中 | ⏳ 待完成 |
|:----------|:----------|:----------|
| 1.场景概览 | 5.Python测试脚本 | |
| 2.流程介绍 | | |
| 3.脚本生成 | | |
| 4.报告写入 | | |

---

### ⚠️ Python 测试脚本生成说明

**生成规则**:
- ✅ 新建一个 Python 文件
- ✅ 包含所有场景的端到端测试用例
- ✅ 每个场景一个测试函数
- ✅ 包含 Setup、Execution、Assertion、Teardown

**即将生成的文件**:
- `jl-skills/generated/test/{date}/scripts/e2e_test.py`

**脚本结构**:
- 导入必要的库（requests, json, pytest 等）
- 配置和常量定义
- 每个场景的测试函数
- 主函数执行所有测试

**场景列表**（共 X 个）:
- TC-001: [场景名称] → `test_scenario_001()`
- TC-002: [场景名称] → `test_scenario_002()`
- TC-003: [场景名称] → `test_scenario_003()`
- ...

---

📋 **确认检查点**

是否开始生成 Python 测试脚本？

- 回复 **确认** → 立即生成脚本并写入文件
- 回复 **调整** → 我将修改生成策略

**请确认：** 是否开始生成 Python 测试脚本？
````

**🛑 STOP HERE - 等待用户确认**

---

## 步骤 5.2: Python 脚本生成与写入

**生成规则**:
1. **脚本结构**: 导入库、配置常量、测试函数、主函数
2. **每个测试函数**: Setup、Execution、Assertion、Teardown
3. **脚本特点**: 使用占位符、包含注释、使用断言、支持独立运行和 pytest

**执行规则**:
- ⚠️ **重要**: Python 脚本内容**直接写入文件，不打印到对话框**
- 只显示文件路径和说明

**输出格式**:

````markdown
### ✅ Python 测试脚本已生成并写入文件

**生成的文件**: `jl-skills/generated/test/{date}/scripts/e2e_test.py`

**脚本统计**:
- ✅ 测试函数: X 个（对应 X 个场景）
- ✅ 包含 Setup、Execution、Assertion、Teardown
- ✅ 支持独立运行和 pytest 运行

**脚本说明**:
- 使用占位符 `{{BASE_URL}}` 和 `{{TOKEN}}`，需要替换为实际值
- 每个测试函数对应一个场景
- 包含详细的注释和断言

**运行方式**:
```bash
# 方式1: 直接运行
python e2e_test.py

# 方式2: 使用 pytest
pytest e2e_test.py
```

---

📋 **确认检查点**

Python 测试脚本生成是否完成？

- 回复 **确认** → 完成测试用例生成流程
- 回复 **调整脚本: [具体说明]** → 我将修改脚本

**请确认：** Python 测试脚本生成是否完成？
````

**🛑 STOP HERE - DO NOT OUTPUT STEP 5.3 UNTIL USER CONFIRMS**

⚠️ **重要**: 用户未回复"确认"前，禁止执行任何后续步骤，禁止输出步骤5.3的内容。