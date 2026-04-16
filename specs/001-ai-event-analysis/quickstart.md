# Quickstart: AI 事件分析 & 行业知识库

**Feature**: 001-ai-event-analysis
**Date**: 2026-04-16

## Prerequisites

- Python 3.11+
- Node.js 18+
- MySQL 8.0+
- Redis 7+
- Docker & Docker Compose (可选)

## Backend Setup

```bash
cd backend/

# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 填入:
#   OPENAI_API_KEY / OPENAI_BASE_URL
#   DATABASE_URL=mysql+aiomysql://user:password@localhost:3306/ai_stock
#   REDIS_URL=redis://localhost:6379

# 3. 初始化数据库
alembic upgrade head

# 4. 启动后端
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Frontend Setup

```bash
cd frontend/

# 1. 安装依赖
npm install

# 2. 配置 API 地址（默认 http://localhost:8000）
# 编辑 .env 或 vite.config.ts

# 3. 启动前端
npm run dev
```

## Docker Compose (一键启动)

```bash
docker compose up -d
```

## Key Dependencies

### Backend

| Package | Version | Purpose |
|---------|---------|---------|
| fastapi | ^0.110 | Web 框架 |
| uvicorn | ^0.29 | ASGI 服务器 |
| sqlalchemy | ^2.0 | ORM |
| sqlmodel | ^0.0.18 | SQLAlchemy + Pydantic 集成 |
| aiomysql | ^0.2 | MySQL 异步驱动（与 SQLAlchemy async 配合；亦可选用 asyncmy） |
| redis | ^5.0 | Redis 客户端 |
| httpx | ^0.27 | HTTP 客户端（调用 LLM API） |
| pydantic | ^2.0 | 数据验证 |
| alembic | ^1.13 | 数据库迁移 |
| apscheduler | ^3.10 | 定时任务 |

### Frontend

| Package | Version | Purpose |
|---------|---------|---------|
| react | ^18.3 | UI 框架 |
| antd | ^5.15 | UI 组件库 |
| zustand | ^4.5 | 状态管理 |
| echarts | ^5.5 | 图表库 |
| react-markdown | ^9.0 | Markdown 渲染 |

## Development Flow

### 1. 后端开发流程

```
定义 Domain Entity → 实现 Repository 接口 → 实现 Application 用例 → 实现 Router → 测试
```

### 2. 前端开发流程

```
定义 Service API → 实现 Application 用例 → 构建 Page + Components → 测试
```

### 3. 联调

```bash
# 后端
cd backend && uvicorn app.main:app --reload

# 前端
cd frontend && npm run dev

# 访问 http://localhost:5173
```

## Testing

```bash
# 后端
cd backend && pytest

# 前端
cd frontend && npm run test
```

## Environment Variables

```env
# 大模型
OPENAI_API_KEY=your_key
OPENAI_BASE_URL=https://api.deepseek.com/v1

# 数据库
DATABASE_URL=mysql+aiomysql://user:password@localhost:3306/ai_stock

# Redis
REDIS_URL=redis://localhost:6379/0

# 可选
LOG_LEVEL=info
CORS_ORIGINS=http://localhost:5173
```
