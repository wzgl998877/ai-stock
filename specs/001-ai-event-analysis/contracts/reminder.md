# API Contract: 大事提醒

**Feature**: 001-ai-event-analysis
**Base Path**: `/api/reminders`

---

## GET /api/reminders

获取提醒列表。

### Query Parameters

| Param | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| status | string | no | pending | 状态筛选: pending / archived / all |
| user_id | string | no | default | 用户标识 |

### Response (200 OK)

```json
{
  "pending": [
    {
      "id": "uuid-xxx",
      "title": "美联储议息会议",
      "event_date": "2026-04-20",
      "industry_tags": ["银行", "非银金融"],
      "status": "pending",
      "remind_3day_sent": true,
      "remind_today_sent": false,
      "created_at": "2026-04-10T08:00:00Z"
    }
  ],
  "archived": [
    {
      "id": "uuid-yyy",
      "title": "全国两会开幕",
      "event_date": "2026-03-05",
      "industry_tags": ["房地产", "建筑材料"],
      "status": "archived",
      "created_at": "2026-02-20T08:00:00Z"
    }
  ]
}
```

---

## POST /api/reminders

创建提醒。

### Request

```json
{
  "title": "美联储议息会议",
  "event_date": "2026-04-20",
  "industry_tags": ["银行", "非银金融"]
}
```

| Field | Type | Required | Validation | Description |
|-------|------|----------|------------|-------------|
| title | string | yes | max: 100 chars | 事件名称 |
| event_date | date | yes | must be future | 事件日期 |
| industry_tags | string[] | no | - | 关联行业 |

### Response (201 Created)

```json
{
  "id": "uuid-xxx",
  "title": "美联储议息会议",
  "event_date": "2026-04-20",
  "status": "pending",
  "is_duplicate": false
}
```

### Error Responses

| Status | Code | Message |
|--------|------|---------|
| 409 | DUPLICATE_TITLE | "已有同名提醒，是否继续添加？" |

---

## PUT /api/reminders/{reminder_id}

更新提醒。

### Request

```json
{
  "title": "美联储议息会议（更新）",
  "event_date": "2026-04-21",
  "industry_tags": ["银行"]
}
```

### Response (200 OK)

更新后的完整提醒对象。

---

## DELETE /api/reminders/{reminder_id}

删除提醒。

### Response (204 No Content)

---

## GET /api/reminders/unread-count

获取未读提醒数量（用于导航栏铃铛红点）。

### Response (200 OK)

```json
{
  "count": 2
}
```

---

## POST /api/reminders/{reminder_id}/trigger-analysis

一键触发提醒事件关联的 AI 分析。

### Response (200 OK)

```json
{
  "event_type": "other",
  "question": "美联储议息会议",
  "industry_tags": ["银行", "非银金融"]
}
```

**Note**: 返回预填信息供前端自动填入分析页。
