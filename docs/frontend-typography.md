# 前端字体规范

> 最后更新：2026-05-10

## 全局配置

**基础设置**（`global.css`）：

| 属性 | 值 |
|------|------|
| `font-family` | `'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif` |
| `font-mono` | `'JetBrains Mono', 'SourceCodePro', 'SFMono-Regular', Consolas, monospace` |
| `font-size` | **未设置**（浏览器默认 16px） |
| `font-feature-settings` | `'ss01' on` |
| `-webkit-font-smoothing` | `antialiased` |

## 字号体系

以 **正文 16px** 为基准，系统内所有字号应遵循以下层级：

| 层级 | 字号 | 字重 | 用途 | 示例 |
|------|------|------|------|------|
| H0 页面大标题 | 30px | 300 | 分析页主标题 | `AnalysisPage` 标题 |
| H1 文章标题 | 26px | 300 | 文章详情页 h1 | `ArticleDetailPage` |
| H2 页面标题 | 22px | 300 | 知识库总标题 | `KnowledgePage` |
| H3 卡片标题 | 16px | 400 | 文章卡片标题 | `ArticleCard` title |
| **正文** | **16px** | 400 | Markdown 正文、摘要 | `markdown-body` |
| 次要正文 | 14px | 400 | 引导提示、副标题 | Tab 按钮、引导文案 |
| 标签 / 日期 | 12px | 300-400 | Tag、日期、行业标签 | 事件类型、行业标签 |
| 辅助计数 | 11px | 400 | "X 篇"、数量标记 | 侧边栏计数 |
| 股票链接 | 13px | 400 | 股票代码可点击链接 | `StockCodeLink` |

## 按组件明细

### 知识库模块

| 组件 | 元素 | 当前字号 | 建议字号 |
|------|------|----------|----------|
| `KnowledgePage` | 知识库总标题 | 22px | 22px |
| `KnowledgePage` | "共 X 篇分析" | 13px | **14px** |
| `KnowledgePage` | 搜索提示文案 | 13px | **14px** |
| `KnowledgePage` | Tab 按钮（global.css） | 14px | 14px |
| `ArticleCard` | 卡片标题 | 15px | **16px** |
| `ArticleCard` | 卡片摘要 | 13px | **14px** |
| `ArticleCard` | 事件类型标签 | 11px | 11px |
| `ArticleCard` | 行业标签 | 11px | 11px |
| `ArticleCard` | 日期 | 12px | 12px |
| `TimelineView` | 日期分组标题 | 13px | **14px** |
| `TimelineView` | "X 篇" 计数 | 11px | 11px |
| `SidebarArticleList` | 侧边栏项目名 | 13px | **14px** |
| `SidebarArticleList` | 侧边栏计数 | 11px | 11px |
| `ArticleDetailPage` | 文章标题 h1 | 26px | 26px |
| `ArticleDetailPage` | 摘要 | 15px | **16px** |
| `ArticleDetailPage` | 正文（markdown-body） | 14px | **16px** |
| `ArticleDetailPage` | "本文关联股票" | 13px | **14px** |
| `ArticleDetailPage` | "相关信息" 标题 | 13px | **14px** |
| `ArticleDetailPage` | "相关信息" 键值对 | 12px | 12px |
| `StockCodeLink` | 股票代码链接 | 12px | **13px** |

### 分析模块

| 组件 | 元素 | 当前字号 | 建议字号 |
|------|------|----------|----------|
| `AnalysisPage` | 页面标题 | 30px | 30px |
| `AnalysisPage` | 引导提示 | 13px | **14px** |
| `AnalysisPage` | 进度状态文字 | 13px | **14px** |
| `AnalysisPage` | 空状态描述 | 13px | **14px** |
| `AnalysisRecordsPage` | 记录标题 | 15px | **16px** |
| `AnalysisRecordsPage` | 空状态标题 | 14px | 14px |
| `AnalysisRecordsPage` | 空状态描述 | 12px | 12px |
| `AnalysisRecordsPage` | 状态标签 | 11px | 11px |
| `AnalysisRecordsPage` | 日期/进度 | 11px | 11px |

### 股票模块

| 组件 | 元素 | 当前字号 | 建议字号 |
|------|------|----------|----------|
| `StockDetailDrawer` | 股票名称 | 根据 Ant Design | 根据组件 |
| `StockDetailDrawer` | 次要信息 | 11px | 11px |
| `AddToWatchlistButton` | 按钮文字 | Ant Design 默认 | Ant Design 默认 |

## 待调整项

以下字号需要统一调整以达到正文 16px 基准：

1. `global.css` — `.markdown-body` 从 14px → **16px**
2. `ArticleCard.tsx` — 标题从 15px → **16px**
3. `ArticleCard.tsx` — 摘要从 13px → **14px**
4. `TimelineView.tsx` — 日期标题从 13px → **14px**
5. `SidebarArticleList.tsx` — 侧边栏项目名从 13px → **14px**
6. `KnowledgePage.tsx` — 副标题从 13px → **14px**
7. `ArticleDetailPage.tsx` — 摘要从 15px → **16px**
8. `ArticleDetailPage.tsx` — 小标题从 13px → **14px**
9. `StockCodeLink.tsx` — 股票代码从 12px → **13px**
10. `AnalysisPage.tsx` — 引导文案从 13px → **14px**
11. `AnalysisRecordsPage.tsx` — 记录标题从 15px → **16px**
