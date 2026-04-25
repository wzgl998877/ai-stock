# API Endpoints: 个股分析界面展示优化与存档

**Feature Branch**: `005-analysis-ui-archive`
**Created**: 2025-04-25

## 新增端点

### GET /api/analysis/records

分析记录列表，按更新时间倒序。

**Query Parameters**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| page | int | 否 | 页码，默认 1 |
| page_size | int | 否 | 每页条数，默认 20 |
| status | string | 否 | 过滤状态：in_progress/completed/stopped |

**Response**:
```json
{
  "items": [
    {
      "article_id": "abc123",
      "title": "沃格光电（603773）深度分析",
      "summary": "综合分析摘要...",
      "article_type": "stock_analysis",
      "status": "completed",
      "analysis_data": {
        "mode": "full",
        "decision": { "action": "买入", "target_price": 0, "confidence": 0.8, "risk_score": 0.3 }
      },
      "create_time": "2026-04-25T16:00:00",
      "update_time": "2026-04-25T16:05:00",
      "stocks": [{ "stock_code": "603773", "stock_name": "沃格光电" }]
    }
  ],
  "total": 15,
  "page": 1,
  "page_size": 20
}
```

### GET /api/analysis/records/{record_id}

单条分析记录详情，返回完整 `analysis_data`。

**Response**:
```json
{
  "article_id": "abc123",
  "title": "沃格光电（603773）深度分析",
  "summary": "综合分析摘要...",
  "content": "完整 Markdown 内容...",
  "article_type": "stock_analysis",
  "status": "completed",
  "analysis_data": {
    "mode": "full",
    "agents": {
      "market_analyst": { "summary": "技术面...", "completed_at": 1714036800000 },
      "fundamentals_analyst": { "summary": "基本面...", "completed_at": 1714036860000 }
    },
    "debates": [
      { "speaker": "bull_researcher", "round": 1, "content": "..." }
    ],
    "decision": {
      "action": "买入", "target_price": 0, "confidence": 0.8,
      "risk_score": 0.3, "reasoning": "..."
    },
    "title": "...", "summary": "...", "industries": ["光学光电子"]
  },
  "create_time": "2026-04-25T16:00:00",
  "update_time": "2026-04-25T16:05:00",
  "stocks": [{ "stock_code": "603773", "stock_name": "沃格光电" }],
  "industries": [{ "industry_code": "XXX", "industry_name": "光学光电子" }]
}
```

## 修改端点

### POST /api/chat/sessions/{id}/stream (StockAnalysisUseCase)

**改动**: 分析流程中增加增量存档逻辑。

| 时机 | 动作 |
|------|------|
| 流程开始 | 创建 `t_analysis_article` 记录，status=in_progress，article_type=stock_analysis |
| 分析师阶段完成 | 更新 analysis_data.agents + update_time |
| 辩论阶段完成 | 更新 analysis_data.debates + update_time |
| 决策产出 | 更新 analysis_data.decision + update_time |
| 风险阶段完成 | 更新 analysis_data（完整数据）+ update_time |
| 全部完成 | 设置 title/summary/industries，status=completed |
| 用户停止 | status=stopped |
| 错误中断 | status=stopped（如果已有部分数据） |

### GET /api/knowledge/articles (已有)

**改动**: 列表查询时，对 `article_type="stock_analysis"` 的记录额外返回 `status` 字段。

## 无需改动的端点

- `POST /api/chat/sessions` — 创建会话，逻辑不变
- `GET /api/analysis/validate-stock` — 股票验证，逻辑不变
- `GET /api/analysis/stock-recent` — 近期分析检查，逻辑不变（但可考虑查询新 status 字段）
