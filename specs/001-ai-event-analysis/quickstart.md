# Quickstart: AI 事件分析 & 行业知识库

**Feature**: 001-ai-event-analysis
**Date**: 2026-04-16

## Prerequisites

- Python 3.11+
- Node.js 18+
- MySQL 8.0+（需启用 ngram 分词）
- Redis 7+
- Docker & Docker Compose（可选，用于一键启动）

## Backend Setup

```bash
cd backend/

# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 填入:
#   OPENAI_API_KEY=sk-xxx
#   OPENAI_BASE_URL=https://api.deepseek.com/v1
#   DATABASE_URL=mysql+aiomysql://root:password@localhost:3306/ai_stock
#   REDIS_URL=redis://localhost:6379/0

# 3. 创建数据库
mysql -u root -p -e "CREATE DATABASE ai_stock CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 4. 初始化数据库（运行迁移）
alembic upgrade head

# 5. 启动后端
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 6. 验证
curl http://localhost:8000/docs  # Swagger UI
```

## Frontend Setup

```bash
cd frontend/

# 1. 安装依赖
npm install

# 2. 配置 API 地址（默认 http://localhost:8000）
# 创建 .env.local:
#   VITE_API_BASE_URL=http://localhost:8000

# 3. 启动前端
npm run dev

# 4. 访问 http://localhost:5173
```

## Docker Compose（一键启动）

```bash
# 启动 MySQL + Redis + 后端 + 前端
docker compose up -d

# 查看日志
docker compose logs -f

# 访问
# 前端: http://localhost:5173
# 后端 API: http://localhost:8000/docs
```

## Key Dependencies

### Backend

| Package | Version | Purpose |
|---------|---------|---------|
| fastapi | ^0.110 | Web 框架 |
| uvicorn | ^0.29 | ASGI 服务器 |
| sqlalchemy | ^2.0 | ORM |
| aiomysql | ^0.2 | MySQL 异步驱动 |
| redis | ^5.0 | Redis 客户端 |
| httpx | ^0.27 | HTTP 客户端（调用 LLM API） |
| pydantic | ^2.0 | 数据验证 |
| alembic | ^1.13 | 数据库迁移 |
| apscheduler | ^3.10 | 定时任务（大事提醒检查） |
| jieba | ^0.42 | 中文分词（相似问题检测） |

### Frontend

| Package | Version | Purpose |
|---------|---------|---------|
| react | ^18.3 | UI 框架 |
| antd | ^5.15 | UI 组件库 |
| zustand | ^4.5 | 状态管理 |
| echarts | ^5.5 | 图表库（预留） |
| react-markdown | ^9.0 | Markdown 渲染 |

## Development Flow

### 1. 后端开发流程（DDD）

```
定义 Domain Entity → 定义 Repository 接口 → 实现 Application 用例
→ 实现 Infrastructure（Repository + AI） → 实现 Router → 测试
```

### 2. 前端开发流程

```
定义 Service API → 实现 Application 用例 → 构建 Page + Components → 测试
```

### 3. 联调

```bash
# 终端1: 后端
cd backend && uvicorn app.main:app --reload

# 终端2: 前端
cd frontend && npm run dev

# 访问 http://localhost:5173
```

## Testing

```bash
# 后端单元测试
cd backend && pytest tests/unit/ -v

# 后端集成测试
cd backend && pytest tests/integration/ -v

# 前端测试
cd frontend && npm run test
```

## Environment Variables

```env
# === 大模型 ===
OPENAI_API_KEY=sk-your-key
OPENAI_BASE_URL=https://api.deepseek.com/v1

# === 数据库 ===
DATABASE_URL=mysql+aiomysql://root:password@localhost:3306/ai_stock

# === Redis ===
REDIS_URL=redis://localhost:6379/0

# === 应用配置 ===
LOG_LEVEL=info
CORS_ORIGINS=http://localhost:5173

# === 可选 ===
# LLM_MODEL=deepseek-chat
# ANALYSIS_TIMEOUT=120
# SIMILARITY_THRESHOLD=0.3
```

## 核心验证路径

1. **分析流程**: 选择事件类型 → 输入描述 → 点击分析 → 看到 SSE 流式输出 → 确认行业标签 → 保存
2. **知识库浏览**: 行业视图 / 时间线视图 / 股票视图切换 → 搜索关键词 → 查看文章详情
3. **大事提醒**: 添加提醒 → 查看提醒列表 → 提醒触发通知
4. **跨模块联动**: 文章中股票代码点击 → 跳转模块二个股详情（需模块二已实现）
