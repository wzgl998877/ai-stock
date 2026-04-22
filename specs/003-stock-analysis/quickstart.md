# Quickstart: 个股多Agent深度分析

**Feature Branch**: `003-stock-analysis`
**Date**: 2026-04-22

---

## 前置条件

- Python 3.10+ 环境
- Node.js 18+ 环境
- MySQL 数据库已运行
- Redis 已运行（可选，用于缓存）
- LLM API Key 已配置（.env 中 `LLM_API_KEY`、`LLM_BASE_URL`、`LLM_MODEL`）
- AKShare 数据源可用（需联网）

## 后端启动

```bash
# 1. 进入后端目录
cd backend

# 2. 安装依赖（新增 langgraph、akshare、baostock）
pip install -r requirements.txt

# 3. 执行数据库迁移（新增 article_type、analysis_data 等字段）
alembic upgrade head

# 4. 启动后端
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 前端启动

```bash
# 1. 进入前端目录
cd frontend

# 2. 安装依赖
npm install

# 3. 启动开发服务器
npm run dev
```

## 验证功能

### 1. 验证后端 API

```bash
# 创建个股分析会话
curl -X POST http://localhost:8000/api/chat/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "title": "宁德时代深度分析",
    "event_type": "stock_analysis",
    "config": {
      "stock_code": "300750",
      "stock_name": "宁德时代",
      "analysis_mode": "full"
    }
  }'

# 验证股票代码
curl http://localhost:8000/api/analysis/validate-stock?keyword=300750

# 发起深度分析（SSE流）
curl -X POST http://localhost:8000/api/chat/sessions/{session_id}/stream \
  -H "Content-Type: application/json" \
  -d '{
    "content": "分析宁德时代",
    "event_type": "stock_analysis",
    "config": {
      "stock_code": "300750",
      "stock_name": "宁德时代",
      "analysis_mode": "full"
    }
  }'
```

### 2. 验证前端页面

1. 打开浏览器访问 `http://localhost:3000`
2. 侧边栏应显示"个股分析"入口
3. 点击进入个股分析页面
4. 输入"宁德时代"或"300750"
5. 选择分析模式（快速/标准/深度）
6. 点击"开始分析"
7. 观察各Agent状态指示和分析结果流式展示

### 3. 验证知识库联动

1. 分析完成后，点击"保存到知识库"
2. 切换到知识库页面
3. 在股票视图中找到"宁德时代"
4. 确认分析文章已关联该股票

## 关键配置

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| `LLM_MODEL` | 快速思考模型 | deepseek-chat |
| `LLM_DEEP_MODEL` | 深度思考模型（用于 Research Manager / Risk Judge） | deepseek-chat |
| `ANALYSIS_TIMEOUT` | 分析超时（秒） | 300 |
| `DEBATE_ROUNDS` | 投资辩论默认轮次 | 2 |
| `RISK_DEBATE_ROUNDS` | 风险辩论默认轮次 | 2 |
| `MAX_TOOL_CALLS` | 分析师最大工具调用次数 | 3 |
| `STOCK_CACHE_TTL` | 股票数据缓存时间（秒） | 300 |
