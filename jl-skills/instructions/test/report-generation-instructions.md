# 报告生成指令 (Report Generation Instructions)

此文档指导 Agent 执行场景测试报告与执行脚本的生成（阶段 3）。

> [!IMPORTANT]
> **目标**: 生成可执行的测试规格书（Markdown），包含场景描述、cURL、SQL 和自动化脚本。
> **原则**: 严禁出现真实敏感数据，必须使用占位符脱敏。

## 步骤 1: 生成概览与逻辑 (Overview & Logic)

1.  **场景概览表**:
    - 列出所有 P0/P1/P2 场景。
    - 表头: ID, 名称, 前置, 预期, 关键点。
2.  **流程图**:
    - 使用 `mermaid sequenceDiagram` 绘制正常/异常流程的时序图。
3.  **交互**:
    - 输出概览和图表。

## 步骤 2: 生成接口脚本 (cURL)

1.  **脚本生成**:
    - 为每个场景生成 cURL 命令。
    - **脱敏**: 使用 `{{BASE_URL}}`, `{{TOKEN}}` 等占位符。
2.  **交互**:
    - 展示脚本样例。

## 步骤 3: 生成数据脚本 (SQL)

1.  **准备脚本**: `INSERT` 语句准备测试数据。
2.  **清理脚本**: `DELETE` 语句清理环境。
3.  **校验脚本**: `SELECT` 语句验证结果状态。
4.  **交互**:
    - 展示 SQL 逻辑。

## 步骤 4: 生成自动化脚本 (Python/Java)

1.  **脚本生成**:
    - 生成 Python (requests) 或 Java (RestAssured) 测试脚本。
    - 包含：Setup, Execution, Assertion, Teardown。
2.  **交互**:
    - 确认生成语言（默认 Python）。
    - 展示完整代码块。

## 步骤 5: 整合与保存

1.  **整合**:
    - 将上述内容填入 `jl-skills/templates/JL-Template-Scenario-Test-Case.md`。
2.  **保存**:
    - 保存为 `Scenario_Test_Case_{timestamp}.md`。
3.  **结束**:
    - 标记流程完成。
