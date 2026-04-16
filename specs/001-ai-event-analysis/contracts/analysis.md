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

```
event: chunk
data: {"type": "content", "text": "## 事件背景\n"}

event: chunk
data: {"type": "content", "text": "美国对伊朗实施新一轮制裁..."}

event: chunk
data: {"type": "meta", "title": "美伊冲突对能源军工影响", "summary": "能源和军工板块短期受益...最大风险是..."}

event: done
data: {"type": "complete", "article_id": null}
```

**Event Types**:
- `chunk (type=content)`: 分析正文内容片段
- `chunk (type=meta)`: 标题和摘要元数据
- `done (type=complete)`: 分析完成
- `error`: 错误信息

### Error Responses

| Status | Code | Message |
|--------|------|---------|
| 400 | INVALID_INPUT | "请输入事件描述" / "描述太简短，请详细说明" |
| 429 | RATE_LIMITED | "分析正在进行中，请稍候" |
| 503 | AI_SERVICE_ERROR | "AI服务暂时不可用，请稍后重试" |

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

检测相似历史文章（不调用 AI，基于关键词匹配）。

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
      "created_at": "2026-01-15T10:30:00Z",
      "similarity": 0.72
    }
  ]
}
```

---

## GET /api/analysis/draft

获取本地草稿（此接口可选，草稿主要在前端 localStorage 管理）。
