# API Contracts: 股票详情页与行情数据展示

**Feature**: 006-stock-detail-kline
**Base Path**: `/api/v1`
**Date**: 2026-04-30

---

## 已有接口（无需修改）

| Method | Path | Description |
|--------|------|-------------|
| GET | `/stocks/{code}` | 股票基础信息 |
| GET | `/stocks/{code}/quote` | 最新实时行情 |
| GET | `/stocks/{code}/daily` | 历史K线数据 |
| GET | `/stocks/{code}/financial` | 财务数据 |

---

## 新增接口

### 1. 分时数据

#### GET /stocks/{code}/minute

获取某只股票当日分时数据（1分钟线）。

**Request**:
```
GET /api/v1/stocks/300750/minute
```

**Response 200**:
```json
{
  "data": {
    "code": "300750",
    "trade_date": "2026-04-30",
    "items": [
      {
        "time": "09:30",
        "price": 245.30,
        "volume": 12500,
        "avg_price": 245.20
      }
    ]
  }
}
```

**Cache**: Redis, TTL=15分钟（交易时段）

---

### 2. 技术指标

#### GET /stocks/{code}/indicators

获取某只股票的技术指标（MA/MACD/KDJ）。

**Query Parameters**:
| Param | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| period | string | No | daily | daily/weekly/monthly |
| indicators | string | No | ma,macd,kdj | 逗号分隔的指标名 |
| start_date | string | No | - | YYYY-MM-DD |
| end_date | string | No | - | YYYY-MM-DD |

**Request**:
```
GET /api/v1/stocks/300750/indicators?period=daily&indicators=ma,macd,kdj
```

**Response 200**:
```json
{
  "data": {
    "code": "300750",
    "period": "daily",
    "items": [
      {
        "trade_date": "2026-04-30",
        "ma5": 240.50,
        "ma10": 235.20,
        "ma20": 228.10,
        "macd_dif": 2.35,
        "macd_dea": 1.80,
        "macd_bar": 0.55,
        "kdj_k": 78.50,
        "kdj_d": 72.30,
        "kdj_j": 90.90
      }
    ]
  }
}
```

**Cache**: Redis, TTL=24小时

---

### 3. 股票搜索

#### GET /stocks/search

模糊搜索股票（代码/名称匹配）。

**Query Parameters**:
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| q | string | Yes | 搜索关键词 |
| limit | int | No | 最大返回数量, default=20 |

**Request**:
```
GET /api/v1/stocks/search?q=宁德&limit=10
```

**Response 200**:
```json
{
  "data": {
    "query": "宁德",
    "total": 3,
    "items": [
      {
        "code": "300750",
        "name": "宁德时代",
        "industry": "电力设备",
        "change_pct": 1.34,
        "price": 245.30
      }
    ]
  }
}
```

**Cache**: Redis, TTL=5分钟

---

#### GET /stocks/all

获取所有活跃股票列表（用于前端本地搜索缓存）。

**Response 200**:
```json
{
  "data": {
    "total": 5123,
    "items": [
      {
        "code": "300750",
        "name": "宁德时代",
        "industry": "电力设备"
      }
    ]
  }
}
```

**Cache**: Redis, TTL=24小时

---

### 4. 自选股

#### GET /watchlist/groups

获取当前用户的所有自选股分组。

**Response 200**:
```json
{
  "data": {
    "groups": [
      {
        "id": 1,
        "name": "重仓股",
        "is_default": true,
        "display_order": 0,
        "stock_count": 5,
        "stocks": [
          {
            "code": "300750",
            "name": "宁德时代",
            "price": 245.30,
            "change_pct": 1.34,
            "industry": "电力设备",
            "signal": "-"
          }
        ]
      }
    ]
  }
}
```

---

#### POST /watchlist/groups

创建新分组。

**Request Body**:
```json
{
  "name": "短线观察"
}
```

**Response 201**:
```json
{
  "data": {
    "id": 4,
    "name": "短线观察",
    "is_default": false,
    "display_order": 3
  }
}
```

**Validation**: name 1-10字符; 每用户最多10个分组

---

#### PUT /watchlist/groups/{group_id}

重命名分组。

**Request Body**:
```json
{
  "name": "新名称"
}
```

**Response 200**:
```json
{
  "data": {
    "id": 4,
    "name": "新名称"
  }
}
```

---

#### DELETE /watchlist/groups/{group_id}

删除分组（默认分组不可删除）。

**Response 200**:
```json
{
  "data": {
    "message": "分组已删除，X只股票已移入观察股"
  }
}
```

---

#### POST /watchlist/groups/{group_id}/stocks

向分组添加股票。

**Request Body**:
```json
{
  "stock_code": "300750",
  "stock_name": "宁德时代"
}
```

**Response 201**:
```json
{
  "data": {
    "id": 100,
    "group_id": 1,
    "stock_code": "300750",
    "stock_name": "宁德时代",
    "add_time": "2026-04-30T10:00:00"
  }
}
```

**Validation**: 每组最多100只; 同一分组内不可重复

---

#### DELETE /watchlist/groups/{group_id}/stocks/{stock_code}

从分组移除股票。

**Response 204**: No Content

---

### 5. 行业数据

#### GET /industries

获取申万一级行业列表。

**Response 200**:
```json
{
  "data": {
    "total": 31,
    "items": [
      {
        "code": "480000",
        "name": "电力设备",
        "display_order": 1
      }
    ]
  }
}
```

---

#### GET /industries/{industry_code}/stocks

获取某行业内的股票对比数据。

**Query Parameters**:
| Param | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| sort_by | string | No | change_pct | 排序字段 |
| sort_order | string | No | desc | asc/desc |
| page | int | No | 1 | 页码 |
| page_size | int | No | 20 | 每页数量 |

**Response 200**:
```json
{
  "data": {
    "industry": {
      "code": "480000",
      "name": "电力设备",
      "avg_change_pct": 0.85
    },
    "total": 156,
    "page": 1,
    "page_size": 20,
    "items": [
      {
        "code": "300750",
        "name": "宁德时代",
        "change_pct": 1.34,
        "pe_ttm": 28.50,
        "pb": 6.20,
        "revenue": 4009.00,
        "net_profit": 441.00,
        "profit_growth_pct": 43.00
      }
    ]
  }
}
```

---

### 6. 相关分析

#### GET /stocks/{code}/related-articles

获取与该股票相关的分析文章。

**Query Parameters**:
| Param | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| limit | int | No | 50 | 最大返回数量 |

**Response 200**:
```json
{
  "data": {
    "code": "300750",
    "total": 3,
    "items": [
      {
        "article_id": 1001,
        "title": "新能源行业深度分析：宁德时代的护城河",
        "summary": "宁德时代在全球动力电池市场占据龙头地位，技术壁垒和产能...",
        "saved_at": "2026-04-15T10:00:00"
      }
    ]
  }
}
```

---

### 7. 个股综合信息（聚合接口）

#### GET /stocks/{code}/detail

获取个股详情页的聚合数据（基础信息+实时行情+最新财务）。

**Response 200**:
```json
{
  "data": {
    "basic": {
      "code": "300750",
      "name": "宁德时代",
      "exchange": "SZ",
      "industry_code": "480000",
      "industry_name": "电力设备",
      "list_date": "2018-06-11",
      "total_market_cap": 10780.50,
      "float_market_cap": 9520.30
    },
    "quote": {
      "price": 245.30,
      "change_pct": 1.34,
      "change_amount": 3.25,
      "volume": 12300000,
      "amount": 3015000000,
      "open_price": 242.50,
      "high_price": 247.00,
      "low_price": 241.00,
      "pre_close": 242.05,
      "pe_ttm": 28.50,
      "pb": 6.20
    },
    "financial": {
      "revenue": 4009.00,
      "revenue_growth_pct": 33.00,
      "net_profit": 441.00,
      "profit_growth_pct": 43.00
    }
  }
}
```

---

## Error Response Format

统一错误格式（与现有系统一致）：

```json
{
  "detail": "股票代码不存在"
}
```

HTTP Status Codes:
| Code | Meaning |
|------|---------|
| 200 | OK |
| 201 | Created |
| 204 | No Content |
| 400 | Bad Request（参数错误） |
| 401 | Unauthorized（未登录） |
| 404 | Not Found（股票/分组不存在） |
| 409 | Conflict（重复添加等） |
| 422 | Validation Error |
| 429 | Too Many Requests |
| 500 | Internal Server Error |
