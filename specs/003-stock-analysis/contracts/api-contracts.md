# API Contracts: 个股多Agent深度分析

**Feature Branch**: `003-stock-analysis`
**Date**: 2026-04-22

---

## API 端点

### 1. 创建个股分析会话

```
POST /api/chat/sessions
```

**Request**:
```json
{
  "title": "宁德时代深度分析",
  "event_type": "stock_analysis",
  "config": {
    "stock_code": "300750",
    "stock_name": "宁德时代",
    "analysis_mode": "full",
    "debate_rounds": 2,
    "risk_debate_rounds": 2
  }
}
```

**Response** (`201 Created`):
```json
{
  "id": "sess_abc123",
  "title": "宁德时代深度分析",
  "event_type": "stock_analysis",
  "config": {
    "stock_code": "300750",
    "stock_name": "宁德时代",
    "analysis_mode": "full",
    "debate_rounds": 2,
    "risk_debate_rounds": 2
  },
  "created_at": "2026-04-22T10:00:00Z"
}
```

---

### 2. 发起个股深度分析（SSE 流式）

```
POST /api/chat/sessions/{session_id}/stream
```

**Request**:
```json
{
  "content": "分析宁德时代",
  "event_type": "stock_analysis",
  "config": {
    "stock_code": "300750",
    "stock_name": "宁德时代",
    "analysis_mode": "full",
    "debate_rounds": 2,
    "risk_debate_rounds": 2
  }
}
```

**Response** (`200 OK`, `Content-Type: text/event-stream`):

SSE 事件流，事件格式为 `data: {json}\n\n`：

#### 事件类型

| 事件 type | data 结构 | 说明 |
|-----------|----------|------|
| `agent_status` | `{agent: string, phase: string, status: "running"\|"done"\|"failed"}` | Agent 开始/完成/失败 |
| `content` | `string` | Agent 分析内容流式块 |
| `reasoning` | `string` | 推理过程流式块 |
| `debate` | `{speaker: string, round: int, content: string}` | 辩论过程 |
| `agent_report` | `{agent: string, summary: string}` | Agent 分析完成摘要 |
| `decision` | `{action: string, target_price: number, confidence: number, risk_score: number, reasoning: string}` | 最终结构化决策 |
| `title` | `string` | 自动生成的标题 |
| `summary` | `string` | 自动生成的摘要 |
| `industries` | `string[]` | 关联行业列表 |
| `error` | `string` | 错误消息 |
| `done` | `""` | 流结束 |

#### SSE 流示例

```
data: {"type": "agent_status", "data": {"agent": "market_analyst", "phase": "analysts", "status": "running"}}

data: {"type": "thinking", "data": {"step": "market_analyst", "status": "running", "message": "正在获取技术面数据..."}}

data: {"type": "content", "data": "宁德时代（300750）技术面分析：\n\n当前价格245.30元..."}

data: {"type": "agent_status", "data": {"agent": "market_analyst", "phase": "analysts", "status": "done"}}

data: {"type": "agent_report", "data": {"agent": "market_analyst", "summary": "短期处于上升通道，MA5上穿MA10形成金叉..."}}

data: {"type": "agent_status", "data": {"agent": "fundamentals_analyst", "phase": "analysts", "status": "running"}}

...

data: {"type": "agent_status", "data": {"agent": "bull_researcher", "phase": "debate", "status": "running"}}

data: {"type": "debate", "data": {"speaker": "bull", "round": 1, "content": "看多论据：新能源赛道持续景气..."}}

data: {"type": "debate", "data": {"speaker": "bear", "round": 1, "content": "看空论据：估值偏高，行业竞争加剧..."}}

...

data: {"type": "decision", "data": {"action": "持有", "target_price": 280.0, "confidence": 0.72, "risk_score": 0.35, "reasoning": "基本面优秀但估值偏高，建议持有等待回调买入机会"}}

data: {"type": "title", "data": "宁德时代深度分析"}

data: {"type": "summary", "data": "新能源龙头基本面优秀，但短期估值偏高需警惕。最大风险为行业竞争加剧导致毛利率下滑。"}

data: {"type": "industries", "data": ["电力设备", "有色金属"]}

data: {"type": "done", "data": ""}
```

---

### 3. 查询股票历史分析

```
GET /api/knowledge/articles?stock_code={code}&article_type=stock_analysis
```

**Response** (`200 OK`):
```json
{
  "items": [
    {
      "id": "art_xyz",
      "title": "宁德时代深度分析",
      "summary": "新能源龙头基本面优秀...",
      "article_type": "stock_analysis",
      "industries": ["电力设备", "有色金属"],
      "stocks": [{"code": "300750", "name": "宁德时代"}],
      "analysis_data": {
        "decision": {
          "action": "持有",
          "target_price": 280.0,
          "confidence": 0.72,
          "risk_score": 0.35
        }
      },
      "created_at": "2026-04-22T10:05:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

---

### 4. 检查股票近期分析

```
GET /api/analysis/stock-recent?stock_code={code}&minutes=5
```

**Response** (`200 OK`):
```json
{
  "has_recent": true,
  "article_id": "art_xyz",
  "title": "宁德时代深度分析",
  "created_at": "2026-04-22T10:05:00Z"
}
```

---

### 5. 股票代码验证

```
GET /api/analysis/validate-stock?keyword={code_or_name}
```

**Response** (`200 OK`):
```json
{
  "valid": true,
  "stock_code": "300750",
  "stock_name": "宁德时代",
  "market": "sz"
}
```

**股票未找到**:
```json
{
  "valid": false,
  "message": "未找到该股票，请检查代码或名称"
}
```

---

## 错误码

| HTTP 状态码 | 错误场景 | 错误消息 |
|-------------|---------|---------|
| 400 | 股票代码无效 | `未找到该股票，请检查代码或名称` |
| 409 | 5分钟内已有分析 | `该股票5分钟内已有分析，是否查看最近的分析结果？` |
| 409 | 已有分析进行中 | `当前有分析进行中，请等待完成或取消后再试` |
| 503 | 数据源不可用 | `该股票数据不可用，无法进行分析` |
| 500 | 分析超时 | `分析超时，已完成的部分结果已保存` |
