# API Contracts: 多数据源股票数据体系

## 1. 数据源配置 API (`/api/v1/datasources`)

### 1.1 列出所有数据源配置

**Request**:
```
GET /api/v1/datasources
```

**Response** `200 OK`:
```json
{
  "data": [
    {
      "source_type": "tushare",
      "api_key_masked": "ts_abc...xyz",
      "is_enabled": true,
      "priority": 1,
      "has_configured": true
    },
    {
      "source_type": "akshare",
      "api_key_masked": null,
      "is_enabled": true,
      "priority": 2,
      "has_configured": true
    },
    {
      "source_type": "baostock",
      "api_key_masked": null,
      "is_enabled": false,
      "priority": 3,
      "has_configured": false
    }
  ]
}
```

### 1.2 配置数据源

**Request**:
```
POST /api/v1/datasources
Content-Type: application/json

{
  "source_type": "tushare",
  "api_key": "ts_xxxxxxxxxxxxxxxxxxxxxx",
  "is_enabled": true,
  "priority": 1
}
```

**Response** `201 Created`:
```json
{
  "data": {
    "source_type": "tushare",
    "api_key_masked": "ts_xxx...xxx",
    "is_enabled": true,
    "priority": 1,
    "has_configured": true
  }
}
```

### 1.3 更新数据源配置

**Request**:
```
PUT /api/v1/datasources/{source_type}
Content-Type: application/json

{
  "api_key": "ts_new_xxxxxxxxxxxxxxxxxxxxxx",
  "is_enabled": true,
  "priority": 1
}
```

**Response** `200 OK`: (同 1.2 response)

### 1.4 删除数据源配置

**Request**:
```
DELETE /api/v1/datasources/{source_type}
```

**Response** `204 No Content`

---

## 2. 同步任务 API (`/api/v1/sync`)

### 2.1 触发同步 (SSE)

**Request**:
```
GET /api/v1/sync/execute?source_type=tushare&data_type=basic_info
Accept: text/event-stream
```

**Query Parameters**:
| Param | Required | Description |
|-------|----------|-------------|
| `source_type` | Yes | `tushare`, `akshare`, `baostock` |
| `data_type` | Yes | `basic_info`, `market_quote`, `daily_quote`, `financial` |
| `symbol` | No | 指定股票代码（单股同步），不传则为全市场同步 |
| `start_date` | No | 历史数据起始日期（仅 `daily_quote`） |
| `end_date` | No | 历史数据结束日期（仅 `daily_quote`） |

**Response** `200 OK` (SSE stream):
```
event: sync_started
data: {"task_id": "uuid-xxx", "source_type": "tushare", "data_type": "basic_info", "total": 5000}

event: sync_progress
data: {"task_id": "uuid-xxx", "processed": 500, "total": 5000, "success": 498, "failed": 2, "status": "running"}

event: sync_progress
data: {"task_id": "uuid-xxx", "processed": 1000, "total": 5000, "success": 996, "failed": 4, "status": "running"}

event: sync_completed
data: {"task_id": "uuid-xxx", "total": 5000, "processed": 5000, "success": 4980, "failed": 20, "duration_ms": 12340}
```

**Error Response** `409 Conflict` (任务已在执行中):
```json
{
  "error": "sync_in_progress",
  "message": "数据源 tushare 的同步任务正在执行中",
  "running_task_id": "uuid-yyy"
}
```

**Error Response** `400 Bad Request` (未配置数据源):
```json
{
  "error": "datasource_not_configured",
  "message": "数据源 tushare 未配置，请先在数据源配置中添加 API Key"
}
```

### 2.2 查询同步历史

**Request**:
```
GET /api/v1/sync/tasks?page=1&page_size=20&source_type=tushare&status=completed
```

**Response** `200 OK`:
```json
{
  "data": {
    "items": [
      {
        "task_id": "uuid-xxx",
        "source_type": "tushare",
        "data_type": "basic_info",
        "status": "completed",
        "total_count": 5000,
        "processed_count": 5000,
        "success_count": 4980,
        "fail_count": 20,
        "start_time": "2026-04-24T10:00:00",
        "end_time": "2026-04-24T10:02:12",
        "duration_ms": 132000
      }
    ],
    "total": 150,
    "page": 1,
    "page_size": 20
  }
}
```

### 2.3 重试失败任务

**Request**:
```
POST /api/v1/sync/tasks/{task_id}/retry
```

**Response** `200 OK`: (触发新同步任务，行为同 2.1)

---

## 3. 股票数据查询 API (`/api/v1/stocks`)

### 3.1 查询股票基础信息

**Request**:
```
GET /api/v1/stocks/{code}
```

**Response** `200 OK`:
```json
{
  "data": {
    "code": "000001",
    "name": "平安银行",
    "exchange": "SZSE",
    "market_type": "CN_A",
    "industry": "银行",
    "list_date": "1991-04-03",
    "is_active": true,
    "data_sources": ["tushare", "akshare"]
  }
}
```

### 3.2 查询股票行情

**Request**:
```
GET /api/v1/stocks/{code}/quote
```

**Response** `200 OK`:
```json
{
  "data": {
    "code": "000001",
    "price": 12.35,
    "change_pct": 1.23,
    "change_amount": 0.15,
    "volume": 58230000,
    "amount": 718500000,
    "quote_time": "2026-04-24T15:00:00",
    "data_source": "tushare"
  }
}
```

### 3.3 查询历史K线

**Request**:
```
GET /api/v1/stocks/{code}/daily?start_date=2026-01-01&end_date=2026-04-24&period=daily
```

**Response** `200 OK`:
```json
{
  "data": {
    "code": "000001",
    "period": "daily",
    "items": [
      {
        "trade_date": "2026-04-24",
        "open": 12.20,
        "high": 12.45,
        "low": 12.15,
        "close": 12.35,
        "volume": 58230000,
        "amount": 718500000,
        "pct_chg": 1.23,
        "data_source": "tushare"
      }
    ]
  }
}
```

### 3.4 查询财务数据

**Request**:
```
GET /api/v1/stocks/{code}/financial
```

**Response** `200 OK`:
```json
{
  "data": {
    "code": "000001",
    "items": [
      {
        "report_date": "2025-12-31",
        "roe": 12.34,
        "net_profit": 45600000000,
        "revenue": 152300000000,
        "eps": 2.35,
        "gross_margin": 68.5,
        "debt_ratio": 92.1,
        "data_source": "tushare"
      }
    ]
  }
}
```

---

## Error Response Format

所有错误响应统一格式:
```json
{
  "error": "error_code",
  "message": "Human readable error message"
}
```

**Error Codes**:
| Code | HTTP Status | Description |
|------|-------------|-------------|
| `datasource_not_configured` | 400 | 数据源未配置 |
| `sync_in_progress` | 409 | 同步任务正在执行 |
| `invalid_source_type` | 400 | 无效的数据源类型 |
| `invalid_data_type` | 400 | 无效的数据类型 |
| `stock_not_found` | 404 | 股票不存在 |
| `sync_failed` | 500 | 同步执行失败 |
| `datasource_api_error` | 502 | 数据源 API 调用失败 |
