# Research: AI 事件分析 & 行业知识库

**Feature**: 001-ai-event-analysis
**Date**: 2026-04-16
**Status**: Complete

---

## 1. SSE 流式输出方案

### Decision
后端使用 FastAPI `StreamingResponse` + `httpx` 异步流式调用 LLM API，前端使用 `fetch` + `ReadableStream` 接收 SSE 事件。

### Rationale
- FastAPI 原生支持 `StreamingResponse`，配合 `async generator` 可实现高效流式输出
- 前端使用 `fetch` + `ReadableStream` 而非 `EventSource`，因为需要 POST 请求携带事件类型和描述 body
- 与 constitution 要求的 `data: {json}\n\n` 格式一致

### Alternatives Considered
- WebSocket: 双向通信能力过剩，增加复杂度
- 长轮询: 体验差，不满足实时性要求
- EventSource: 仅支持 GET 请求，无法携带 POST body

### SSE 事件协议

```json
// 内容块（流式输出）
data: {"type": "content", "data": "## 事件背景\n简述..."}

// 标题（分析流末尾由后端提取 TITLE: 行）
data: {"type": "title", "data": "美伊冲突对能源军工影响"}

// 摘要（分析流末尾由后端提取 SUMMARY: 行）
data: {"type": "summary", "data": "能源和军工板块短期受益..."}

// 行业标签（后端从内容中解析）
data: {"type": "industries", "data": ["石油石化", "国防军工"]}

// 错误
data: {"type": "error", "data": "AI服务暂时不可用"}

// 完成
data: {"type": "done", "data": ""}
```

后端在流式转发 LLM 输出时，实时监控 `TITLE:` 和 `SUMMARY:` 标记行，提取后通过独立事件类型推送。

---

## 2. Prompt 模板管理方案

### Decision
使用 Python 模块化管理，每种事件类型一个独立 Python 文件（`infrastructure/ai/prompts/`），包含完整的 system prompt 模板。

### Rationale
- Constitution 要求 Prompt 模板化管理，禁止硬编码
- Python 文件比 Jinja2 模板更灵活，可包含格式化逻辑
- 按事件类型分文件，职责清晰，易于维护和扩展
- 5种模板：geopolitical / policy / earnings / supply_chain / general

### Alternatives Considered
- Jinja2 模板文件: 增加额外依赖，对于纯文本替换不必要
- 数据库存储: 过度设计，模板变更频率低
- YAML 配置: 多行文本可读性差

### Implementation Notes
- 每个模板文件导出一个函数，接收 `user_input` 参数，返回完整 prompt 字符串
- 模板中注入申万31个一级行业列表（从 `data/industries.json` 加载）
- 产业链分析模板额外注入传导表格式要求

---

## 3. 全文搜索方案

### Decision
使用 MySQL **InnoDB FULLTEXT** 索引，配合 **ngram** 解析器（token_size=2）实现中文模糊搜索。

### Rationale
- Constitution 明确使用 **MySQL** 作为主库
- ngram FULLTEXT 对中文短词有一定支持，运维上仍为单库方案
- 无额外服务依赖（对比 Elasticsearch），降低运维复杂度
- 数据量在 MVP 阶段（预计几百到几千篇文章）完全够用

### Alternatives Considered
- Elasticsearch: 功能强大但引入额外服务，MVP 阶段过度
- jieba 分词 + 倒排索引: 实现复杂度高，内置 FULLTEXT 已能满足基本需求
- 向量搜索（独立向量库或插件）: 适合语义搜索但增加复杂度，Phase 2 考虑

### Implementation Notes
- 建表时创建：`FULLTEXT INDEX ft_search (title, summary, content) WITH PARSER ngram`
- 查询使用：`MATCH(title, summary, content) AGAINST(query IN BOOLEAN MODE)`
- 行业标签和股票代码通过关联表 JOIN 搜索（精确匹配）

---

## 4. 相似问题检测方案

### Decision
基于标题 + 摘要 + 行业标签的关键词重叠匹配（Jaccard 相似度），不调用 AI。使用 jieba 分词。

### Rationale
- PRD 明确要求不调用 AI（不产生额外费用）
- 关键词重叠匹配实现简单，响应快速
- 有了摘要字段后，匹配维度比纯标题更丰富

### Alternatives Considered
- 向量嵌入相似度: 需要额外 embedding 调用，产生费用
- TF-IDF: 实现较复杂，数据量小时效果不明显
- 编辑距离: 对中文效果差

### Implementation Notes
- 用户停止输入 1 秒后触发（前端 debounce）
- 后端分词后与文章标题/摘要分词结果比对
- Jaccard ≥ 0.3 视为相似（可配置）
- 知识库为空时直接跳过

---

## 5. 分析结果解析方案

### Decision
后端实时解析 LLM 流式输出，按 `##` 标题分隔符拆分章节，同时提取 TITLE/SUMMARY 行。

### Rationale
- LLM 输出格式通过 Prompt 严格约束为"六段/七段"结构，每个章节以 `## 标题` 分隔
- 后端解析可确保前端接收到的结构化数据一致
- 解析失败时降级展示原始内容（Edge Case 处理）

### Implementation Notes
- `AnalysisParser`（Domain Service）负责解析逻辑
- 解析流程：逐行扫描 → 识别 `##` 分隔符 → 拆分为章节字典 → 提取 TITLE/SUMMARY 行
- 产业链传导表：识别 Markdown 表格格式，解析为结构化 JSON
- 降级策略：解析失败时将原始内容作为单段落返回，前端标注"格式解析异常"

---

## 6. 后台任务管理方案

### Decision
分析任务在后端以异步任务方式执行（FastAPI Background Tasks），通过 SSE 推送进度；前端使用 Zustand store 跟踪任务状态。任务 ID 存入 Redis（TTL 5分钟）。

### Rationale
- 用户切换页面后分析不中断：后端 async 任务独立运行
- 任务完成后通过全局状态条通知用户
- 不需要 Celery 等外部任务队列（单用户场景，FastAPI async 足够）

### Alternatives Considered
- Celery + Redis: 引入额外复杂度，MVP 不需要
- WebSocket 推送: SSE 已满足单向推送需求

---

## 7. 草稿自动保存方案

### Decision
前端使用 localStorage 自动保存输入内容（超过20字时），防抖间隔1秒，页面加载时自动恢复。

### Rationale
- localStorage 无需后端接口，实现简单
- 20字阈值避免保存过短的无意义内容
- 刷新页面后自动恢复，体验流畅

### Implementation Notes
- key 格式：`draft:analysis:{event_type}`
- 保存内容：`{ content: string, eventType: string, updatedAt: timestamp }`
- 分析提交成功后清除对应草稿

---

## 8. 大事提醒调度方案

### Decision
使用 APScheduler 定时任务，每天固定时间（如 8:00）检查即将到期的事件，站内通知通过 Redis 缓存未读提醒数量。

### Rationale
- Constitution 技术栈已包含 APScheduler
- 定时任务简单可靠，适合每天检查一次到期事件
- 站内通知不需要实时推送

### Implementation Notes
- 定时任务每日检查：未来3天内的事件设置提醒标记
- 前端登录时调用 `/api/reminders/pending` 获取未读提醒数量
- 用户查看后标记已读
