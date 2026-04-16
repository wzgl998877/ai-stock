# Research: AI 事件分析 & 行业知识库

**Feature**: 001-ai-event-analysis
**Date**: 2026-04-16

## 1. SSE 流式输出方案

### Decision
后端使用 FastAPI `StreamingResponse` + 前端使用 `EventSource` (或 `fetch` + `ReadableStream`)。

### Rationale
- FastAPI 原生支持 `StreamingResponse`，配合 `async generator` 可实现高效流式输出
- 前端 `EventSource` 是 SSE 标准接口，但仅支持 GET 请求；对于 POST 分析请求，使用 `fetch` + `ReadableStream` 解析 SSE 格式
- 与 constitution 要求的 `data: xxx\n\n` 格式一致

### Alternatives Considered
- WebSocket: 双向通信能力过剩，增加复杂度
- 长轮询: 体验差，不满足实时性要求
- 第三方 SSE 库: 不必要，原生能力足够

## 2. Prompt 模板管理方案

### Decision
使用 Python 模块化管理，每种事件类型一个独立 Python 文件，包含完整的 system prompt 模板。

### Rationale
- Constitution 要求 Prompt 模板化管理，禁止硬编码
- Python 文件比 Jinja2 模板更灵活，可包含格式化逻辑
- 按事件类型分文件，职责清晰，易于维护和扩展
- 5种模板：geopolitical / policy / earnings / supply_chain / general

### Alternatives Considered
- Jinja2 模板文件: 增加额外依赖，对于纯文本替换不必要
- 数据库存储: 过度设计，模板变更频率低
- YAML 配置: 多行文本可读性差

## 3. 全文搜索方案

### Decision
使用 MySQL **InnoDB FULLTEXT** 索引，配合 **ngram** 解析器实现中文模糊搜索。

### Rationale
- Constitution 明确使用 **MySQL** 作为主库
- ngram FULLTEXT 对中文短词有一定支持，运维上仍为单库方案
- 无额外服务依赖（对比 Elasticsearch），降低运维复杂度
- 数据量在 MVP 阶段（预计几百到几千篇文章）完全够用

### Alternatives Considered
- Elasticsearch: 功能强大但引入额外服务，MVP 阶段过度
- jieba 分词 + 倒排索引: 实现复杂度高，内置 FULLTEXT 已能满足基本需求
- 向量搜索（独立向量库或插件）: 适合语义搜索但增加复杂度，Phase 2 考虑

## 4. 相似问题检测方案

### Decision
基于标题 + 摘要 + 行业标签的关键词重叠匹配（Jaccard 相似度），不调用 AI。

### Rationale
- PRD 明确要求不调用 AI（不产生额外费用）
- 关键词重叠匹配实现简单，响应快速
- 有了摘要字段后，匹配维度比纯标题更丰富

### Alternatives Considered
- 向量嵌入相似度: 需要额外 embedding 调用，产生费用
- TF-IDF: 实现较复杂，数据量小时效果不明显
- 编辑距离: 对中文效果差

## 5. 后台任务管理方案

### Decision
分析任务在后端以异步任务方式执行，通过 SSE 推送进度；前端使用 Zustand store 跟踪任务状态。

### Rationale
- 用户切换页面后分析不中断：后端 async 任务独立运行
- 任务完成后通过全局状态条通知用户
- 不需要 Celery 等外部任务队列（单用户场景，FastAPI async 足够）

### Alternatives Considered
- Celery + Redis: 引入额外复杂度，MVP 不需要
- WebSocket 推送: SSE 已满足单向推送需求

## 6. 草稿自动保存方案

### Decision
前端使用 localStorage 自动保存输入内容（超过20字时），页面加载时自动恢复。

### Rationale
- localStorage 无需后端接口，实现简单
- 20字阈值避免保存过短的无意义内容
- 刷新页面后自动恢复，体验流畅

### Alternatives Considered
- 后端保存: 需要额外接口，增加复杂度
- IndexedDB: 对于纯文本存储，localStorage 足够

## 7. 大事提醒调度方案

### Decision
使用 APScheduler 定时任务，每天检查即将到期的提醒事件。

### Rationale
- Constitution 技术栈已包含 APScheduler
- 定时任务简单可靠，适合每天检查一次到期事件
- 站内通知通过 Redis 缓存未读提醒数量

### Alternatives Considered
- 纯前端定时器: 页面关闭后无法触发
- 操作系统级定时任务: 与应用耦合度高
