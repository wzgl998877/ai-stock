# 文档更新指令 (Update Docs Instructions)

## ⚠️ 执行规则 (EXECUTION RULES)

```
🛑 CRITICAL: 
- 每个步骤输出后 MUST STOP
- 等待用户回复后才能继续
- 一次回复只输出一个步骤的内容
- 违反此规则将导致流程失败
```

此文档指导 Agent 根据最近生成的工件，更新项目的 Changelog 和 Feature 归档。

> [!IMPORTANT]
> **目标**: 保持文档与代码/设计同步。
> **输入**: 最近生成的 `jl-skills/generated/` 目录下的 `Requirements_Design`, `Scenario_Test_Case`, `Review_Report` 等。

## 步骤 1: 扫描与收集

**你必须输出以下内容，然后停止**:

1.  **扫描**: 查找 `jl-skills/generated/` 目录中最近 24 小时内生成的 Markdown 文件。
2.  **提取**:
    - 从 Requirements 文档提取“新增功能”。
    - 从 Review 报告提取“修复 Bug”和“优化”。
    - 从 Scenario 测试提取“测试覆盖范围”。
3.  **交互**:
    - 询问版本号 (Version) 和变更主题 (Summary)。

## 步骤 2: 更新 CHANGELOG

1.  **渲染**: 基于模板 `jl-skills/templates/JL-Template-Changelog.md`。
2.  **分类**: 将提取的信息归类为 Added, Changed, Fixed, Optimized。
3.  **保存**: 生成 `docs/CHANGELOG/{{version}}-{{summary}}.md`。

## 步骤 3: 归档 Feature 文档

1.  **识别模块**: 询问用户这些文档属于哪个业务模块（如 `Order`, `Payment`）。
2.  **归档操作**:
    - 创建/确认目录 `docs/FEATURES/{{module}}/`。
    - 将 `Requirements_Design_*.md` 复制并重命名为 `docs/FEATURES/{{module}}/SPEC.md`。
    - 将 `Scenario_Test_Case_*.md` 复制并重命名为 `docs/FEATURES/{{module}}/QA.md`。
    - 将 `DDD_Design_*.md` 复制并重命名为 `docs/FEATURES/{{module}}/DESIGN.md`。
    - 将 Python 测试脚本（如 `CaseTest{spec}{time}.py`）复制到 `docs/FEATURES/{{module}}/`。

## 步骤 4: 更新 README 索引

1.  **读取**: 读取项目根目录 `README.md`。
2.  **更新**:
    - 更新“最新版本”信息。
    - 在“功能列表”或“文档索引”章节，添加指向新归档文档的链接。

## 步骤 5: 完成

1.  **反馈**: 列出所有更新和归档的文件路径。
