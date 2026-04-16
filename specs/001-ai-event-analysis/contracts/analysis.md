# API Contract: AI 分析

**Feature**: 001-ai-event-analysis
**Base Path**: `/api/analysis`

---

## POST /api/analysis/stream

启动 AI 事件分析，以 SSE 流式返回结果。

### Request

```json
{
  "event_type": "geopolitical",
  "question": "美国对伊朗实施新一轮制裁，对A股有什么影响？"
}
```

| Field | Type | Required | Validation | Description |
|-------|------|----------|------------|-------------|
| event_type | string | yes | enum: geopolitical, policy, earnings, supply_chain, other | 事件类型 |
| question | string | yes | min: 10 chars, max: 500 chars | 用户输入的事件描述 |

### Response (SSE Stream)

SSE 格式统一为 `data: {json}\n\n`，前端通过 `fetch` + `ReadableStream` 接收（非 EventSource，因需 POST）。

```
data: {"type": "content", "data": "## 事件背景\n"}

data: {"type": "content", "data": "美国对伊朗实施新一轮制裁..."}

data: {"type": "title", "data": "美伊冲突对能源军工影响"}

data: {"type": "summary", "data": "能源和军工板块短期受益，油价上涨传导至化工成本。最大风险是..."}

data: {"type": "industries", "data": ["石油石化", "国防军工", "基础化工"]}

data: {"type": "done", "data": ""}
```

**Event Types**:
- `content`: 分析正文内容片段（流式推送）
- `title`: AI 生成的标题（≤15字）
- `summary`: AI 生成的摘要（≤80字）
- `industries`: AI 提取的行业标签列表
- `error`: 错误信息
- `done`: 分析完成

**TITLE/SUMMARY 提取逻辑**: 后端在流式转发 LLM 输出时，实时监控 `TITLE:` 和 `SUMMARY:` 标记行，提取后通过独立事件类型推送。

### Error Responses

| Status | Code | Message |
|--------|------|---------|
| 400 | INVALID_INPUT | "请输入事件描述" / "描述太简短，请详细说明" |
| 429 | RATE_LIMITED | "分析正在进行中，请稍候" |
| 503 | AI_SERVICE_ERROR | "AI服务暂时不可用，请稍后重试" |

**重试机制**: 后端自动重试最多2次（间隔5秒）。全部失败后返回 `error` 事件，前端保留用户输入内容。

---

## POST /api/analysis/articles

保存分析结果到知识库。

### Request

```json
{
  "title": "美伊冲突对能源军工影响",
  "summary": "能源和军工板块短期受益，油价上涨传导至化工成本。最大风险是地缘冲突快速降温导致行情反转。",
  "content": "## 事件背景\n...(完整 Markdown 正文)",
  "event_type": "geopolitical",
  "raw_input": "美国对伊朗实施新一轮制裁，对A股有什么影响？",
  "industry_tags": ["石油石化", "国防军工", "基础化工"],
  "mentioned_stocks": [
    {"code": "601857", "name": "中国石油", "industry": "石油石化"},
    {"code": "600316", "name": "洪都航空", "industry": "国防军工"}
  ],
  "chain_table": null
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| title | string | yes | 文章标题（≤15字） |
| summary | string | yes | 文章摘要（≤80字） |
| content | string | yes | 完整 Markdown 正文 |
| event_type | string | yes | 事件类型枚举 |
| raw_input | string | yes | 用户原始输入 |
| industry_tags | string[] | yes | 行业标签列表（至少1个或"未分类"） |
| mentioned_stocks | object[] | no | 提及的股票列表 |
| chain_table | object[] | no | 产业链传导表（仅 supply_chain 类型） |

### Response (201 Created)

```json
{
  "id": "uuid-xxx",
  "title": "美伊冲突对能源军工影响",
  "industry_count": 3,
  "created_at": "2026-04-16T10:30:00Z"
}
```

### Error Responses

| Status | Code | Message |
|--------|------|---------|
| 400 | NO_INDUSTRY_TAG | "请至少保留1个行业，或选择「未分类」" |
| 400 | EMPTY_CONTENT | "分析内容不能为空" |

---

## POST /api/analysis/similarity

检测相似历史文章（不调用 AI，基于关键词 Jaccard 相似度匹配）。

### Request

```json
{
  "question": "中东局势对能源股的影响",
  "top_k": 3
}
```

### Response (200 OK)

```json
{
  "similar_articles": [
    {
      "id": "uuid-xxx",
      "title": "美伊冲突对能源军工影响",
      "summary": "能源和军工板块短期受益...",
      "industry_tags": ["石油石化", "国防军工"],
      "created_at": "2026-01-15T10:30:00Z",
      "similarity": 0.72
    }
  ]
}
```

**Note**: 相似度阈值 ≥ 0.3 才返回。知识库为空时返回空列表。
