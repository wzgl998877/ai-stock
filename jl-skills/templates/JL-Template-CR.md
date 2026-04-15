# 代码审查报告

> **日期**: {Timestamp}
> **总体评分**: {Score}/100 (Pass/Fail)

## 1. 审查摘要 (Executive Summary)
>总结审查范围和结果
{Summary_Content}

## 2. 代码核心规约检查 (Compliance Check)
| 检查项 | 状态 | 备注 |
| :--- | :--- | :--- |
| Java 命名规范 | ✅ / ❌ | ... |
| 异常处理 (No Swallow) | ✅ / ❌ | ... |
| 安全性 (OWASP) | ✅ / ❌ | ... |
| 单元测试覆盖 | ✅ / ❌ | ... |

## 3. 架构设计检查
| 检查维度 | 评分 (1-5) | 发现的问题 / 异味 |
| :--- | :--- | :--- |
| **封装性** | [1-5] | [描述] |
| **聚合边界** | [1-5] | [描述] |
| **领域逻辑** | [1-5] | [描述] |
| **值对象使用** | [1-5] | [描述] |

## 4. 详细发现 (Detailed Findings)

### 🔴 严重问题 (Critical)
* **Line {Line_Num}**: {Issue_Description}
    * *违反规则*: {Rule_ID}
    * *修复建议*: `{Fixed_Code_Snippet}`

### 🟡 改进建议 (Major/Minor)
* **Line {Line_Num}**: {Issue_Description}
    * *建议*: ...

## 4. 结论与下一步
> 描述审查结果，并给出下一步建议
{Conclusion}