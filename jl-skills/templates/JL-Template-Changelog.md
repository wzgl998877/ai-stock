# [{{version}}] {{summary}} 变更记录

## 📅 基本信息
- **发布日期**: {{date}}
- **关联需求**: {{requirements_link}}

## 🚀 核心变更 (What's New)
{{#each added}}
- **新增**: {{this}}
{{/each}}
{{#each changed}}
- **优化**: {{this}}
{{/each}}
{{#each fixed}}
- **修复**: {{this}}
{{/each}}

## ⚠️ 兼容性与影响 (Impact Analysis)
| 影响域 | 描述 | 应对措施 |
| :--- | :--- | :--- |
{{#each impact}}
| **{{this.area}}** | {{this.desc}} | {{this.action}} |
{{/each}}

## 📝 详细需求清单
1. [P0] ...
