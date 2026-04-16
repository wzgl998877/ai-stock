# API Contract: 知识库

**Feature**: 001-ai-event-analysis
**Base Path**: `/api/knowledge`

---

## GET /api/knowledge/articles

获取知识库文章列表，支持分页、筛选和排序。

### Query Parameters

| Param | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| view | string | no | timeline | 视图模式: timeline / industry / stock |
| industry | string | no | - | 按行业筛选（industry 视图必填） |
| stock_code | string | no | - | 按股票代码筛选（stock 视图必填） |
| keyword | string | no | - | 全文搜索关键词 |
| page | int | no | 1 | 页码 |
| page_size | int | no | 20 | 每页条数（最大 50） |
| user_id | string | no | default | 用户标识 |

### Response (200 OK)

```json
{
  "total": 42,
  "page": 1,
  "page_size": 20,
  "items": [
    {
      "id": "uuid-xxx",
      "title": "美伊冲突对能源军工影响",
      "summary": "能源和军工板块短期受益，油价上涨传导至化工成本。最大风险是...",
      "industry_tags": ["石油石化", "国防军工"],
      "mentioned_stocks": [{"code": "601857", "name": "中国石油"}],
      "event_type": "geopolitical",
      "created_at": "2026-04-16T10:30:00Z"
    }
  ]
}
```

---

## GET /api/knowledge/articles/{article_id}

获取文章详情。

### Response (200 OK)

```json
{
  "id": "uuid-xxx",
  "title": "美伊冲突对能源军工影响",
  "summary": "能源和军工板块短期受益...",
  "content": "## 事件背景\n完整 Markdown 正文...",
  "event_type": "geopolitical",
  "raw_input": "美国对伊朗实施新一轮制裁...",
  "industry_tags": ["石油石化", "国防军工", "基础化工"],
  "mentioned_stocks": [
    {"code": "601857", "name": "中国石油", "industry": "石油石化"}
  ],
  "chain_table": null,
  "created_at": "2026-04-16T10:30:00Z",
  "updated_at": "2026-04-16T10:30:00Z"
}
```

---

## DELETE /api/knowledge/articles/{article_id}

删除文章。

### Response (204 No Content)

---

## GET /api/knowledge/industries

获取有文章的行业列表（用于行业视图左侧导航）。

### Response (200 OK)

```json
{
  "industries": [
    {
      "name": "石油石化",
      "article_count": 5
    },
    {
      "name": "国防军工",
      "article_count": 3
    }
  ]
}
```

---

## GET /api/knowledge/watchlist-stocks

获取自选股列表及其关联文章数（用于股票视图，数据来自模块三/模块二）。

### Response (200 OK)

```json
{
  "stocks": [
    {
      "code": "601857",
      "name": "中国石油",
      "article_count": 3
    },
    {
      "code": "600519",
      "name": "贵州茅台",
      "article_count": 1
    }
  ]
}
```

**Note**: 自选股数据来源于模块二/三，此接口为跨模块联动预留。

---

## GET /api/knowledge/search

全文搜索知识库文章。

### Query Parameters

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| q | string | yes | 搜索关键词 |
| page | int | no | 页码（默认 1） |
| page_size | int | no | 每页条数（默认 20） |

### Response (200 OK)

与 `GET /api/knowledge/articles` 格式相同，额外包含 `highlight` 字段：

```json
{
  "total": 5,
  "items": [
    {
      "id": "uuid-xxx",
      "title": "美伊冲突对能源军工影响",
      "summary": "...",
      "highlight": "美国对伊朗实施新一轮<em>制裁</em>..."
    }
  ]
}
```
