# API Contracts: 投资事件影响雷达

**Branch**: `007-event-radar` | **Date**: 2026-05-11

## Base URL

所有端点前缀: `/api/v1/event-radar`

## 认证

所有端点需要用户认证（Bearer Token），自动注入 `user_id`，数据按用户隔离。

---

## 1. 影响雷达面板

### GET /impacts

获取当前用户的影响事件列表。

**Query Parameters**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| status | string | 否 | active(活跃) / archived(已归档) / all，默认 all |
| date | string | 否 | 日期过滤，格式 YYYY-MM-DD，默认今天 |

**Response 200**:
```json
{
  "active_impacts": [
    {
      "id": 1,
      "event_id": 101,
      "title": "国际油价突破 85 美元/桶",
      "summary": "...",
      "event_type": "geopolitical",
      "sentiment": "positive",
      "importance": "high",
      "source_count": 3,
      "matched_stocks": [
        {"code": "601857", "name": "中国石油", "direction": "positive", "confidence": 0.85}
      ],
      "matched_industries": [
        {"name": "石油石化", "direction": "positive"}
      ],
      "priority": "P0",
      "is_read": false,
      "has_ai_insight": true,
      "has_related_analysis": true,
      "first_seen_at": "2026-05-11T14:20:00",
      "source_name": "财联社",
      "source_url": "https://..."
    }
  ],
  "archived_impacts": [...],
  "stats": {
    "today_total": 7,
    "today_positive": 4,
    "today_negative": 2,
    "today_neutral": 1,
    "affected_stocks_count": 3,
    "week_total": 23
  },
  "last_scan_at": "2026-05-11T14:30:00"
}
```

---

### GET /impacts/{id}

获取单条影响事件详情。

**Response 200**:
```json
{
  "id": 1,
  "event_id": 101,
  "title": "...",
  "summary": "...",
  "event_type": "geopolitical",
  "sentiment": "positive",
  "importance": "high",
  "source_count": 3,
  "matched_stocks": [...],
  "matched_industries": [...],
  "priority": "P0",
  "is_read": false,
  "first_seen_at": "...",
  "articles": [
    {
      "article_id": 1,
      "title": "...",
      "content": "...",
      "source": "cls",
      "url": "https://...",
      "published_at": "..."
    }
  ],
  "ai_insight": {
    "event_nature": "地缘政治 + 大宗商品",
    "affected_industries_detail": [
      {"name": "石油石化", "direction": "positive", "reason": "油价上涨直接提升上游利润"}
    ],
    "stock_impact_reasons": [
      {"code": "601857", "name": "中国石油", "reason": "油价上涨直接提升上游勘探开采利润"}
    ]
  },
  "related_analyses": [
    {
      "article_id": 50,
      "title": "中东局势对能源板块影响",
      "analyzed_at": "2026-04-15",
      "summary": "短期利好石油石化..."
    }
  ]
}
```

---

### POST /impacts/{id}/ai-insight

生成或获取 AI 解读（幂等：已生成则返回缓存）。

**Response 200**:
```json
{
  "event_nature": "地缘政治 + 大宗商品",
  "affected_industries_detail": [...],
  "stock_impact_reasons": [...]
}
```

---

### GET /stats

获取影响概览统计。

**Response 200**:
```json
{
  "today_total": 7,
  "today_positive": 4,
  "today_negative": 2,
  "today_neutral": 1,
  "affected_stocks_count": 3,
  "week_total": 23
}
```

---

## 2. 预警推送

### GET /alerts

获取未读预警列表。

**Query Parameters**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| limit | int | 否 | 返回数量，默认 10 |

**Response 200**:
```json
{
  "alerts": [
    {
      "id": 1,
      "priority": "P0",
      "title": "国际油价突破 85 美元/桶",
      "summary": "影响你的投资：中国石油 ▲ 利好 85%",
      "user_impact_id": 1,
      "is_read": false,
      "created_at": "2026-05-11T14:20:00"
    }
  ]
}
```

---

### GET /alerts/unread-count

获取未读预警数量。

**Response 200**:
```json
{
  "count": 3
}
```

---

### PUT /alerts/{id}/read

标记预警已读。

**Response 200**:
```json
{
  "success": true
}
```

---

## 3. 影响晨报

### GET /briefing/today

获取今日晨报。

**Response 200**:
```json
{
  "id": 1,
  "briefing_date": "2026-05-11",
  "ai_summary": "昨晚到今晨，2个事件影响你的自选股，整体偏利好。",
  "content": {
    "impact_events": [
      {
        "event_id": 101,
        "title": "美国对伊朗实施新一轮制裁",
        "sentiment": "positive",
        "matched_stocks": [...],
        "source_count": 3
      }
    ],
    "portfolio_overview": [
      {
        "code": "300750",
        "name": "宁德时代",
        "last_close": 245.30,
        "direction": "positive",
        "news_count": 3
      }
    ],
    "today_focus": [
      {"time": "10:00", "event": "公布 4 月 CPI 数据"},
      {"time": "", "event": "宁德时代股东大会"}
    ]
  },
  "is_read": false,
  "created_at": "2026-05-11T06:30:00"
}
```

**Response 404**: 今日晨报未生成

---

### GET /briefing/history

获取历史晨报列表（最近 7 天）。

**Response 200**:
```json
{
  "briefings": [
    {
      "id": 1,
      "briefing_date": "2026-05-11",
      "ai_summary": "...",
      "is_read": false
    }
  ]
}
```

---

### PUT /briefing/{id}/read

标记晨报已读。

**Response 200**:
```json
{
  "success": true
}
```

---

## 4. 配置

### GET /config

获取用户雷达配置。

**Response 200**:
```json
{
  "focused_industries": ["电力设备", "石油石化"],
  "event_types": ["policy", "earnings", "industry", "macro", "geopolitical"],
  "alert_sensitivity": "medium",
  "quiet_hours_start": null,
  "quiet_hours_end": null
}
```

---

### PUT /config

更新用户雷达配置。

**Request Body**:
```json
{
  "focused_industries": ["电力设备", "石油石化", "军工"],
  "event_types": ["policy", "geopolitical"],
  "alert_sensitivity": "high",
  "quiet_hours_start": "22:00:00",
  "quiet_hours_end": "07:00:00"
}
```

**Response 200**:
```json
{
  "success": true
}
```

---

## 5. 自选股影响增强

### GET /stock-impacts

批量获取自选股影响状态（为自选股页面徽标提供数据）。

**Response 200**:
```json
{
  "stocks": [
    {
      "code": "300750",
      "name": "宁德时代",
      "impact_count_24h": 3,
      "direction": "positive",
      "recent_impacts": [
        {
          "event_title": "宁德时代4月出货量同比增长35%",
          "direction": "positive",
          "confidence": 0.72,
          "event_id": 102,
          "user_impact_id": 2
        }
      ]
    },
    {
      "code": "601857",
      "name": "中国石油",
      "impact_count_24h": 2,
      "direction": "positive",
      "recent_impacts": [...]
    }
  ]
}
```

---

## 错误响应格式

所有端点使用统一的错误格式：

```json
{
  "detail": "错误描述信息"
}
```

| 状态码 | 场景 |
|--------|------|
| 401 | 未认证 |
| 403 | 无权限（数据隔离） |
| 404 | 资源不存在 |
| 422 | 参数验证失败 |
| 500 | 服务器内部错误 |
