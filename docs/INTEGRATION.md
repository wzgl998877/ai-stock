# 集成说明 (INTEGRATION)

> 最后更新: 2026-04-16 | 版本: v0.0.1

## 外部服务依赖

### 大模型服务

- **服务**: OpenAI / DeepSeek 兼容接口
- **用途**: AI 事件分析、结构化摘要生成、标题与标签自动提取
- **配置项**:
  - `OPENAI_API_KEY`: API 密钥
  - `OPENAI_BASE_URL`: 接口地址
  - `DEEPSEEK_API_KEY`: DeepSeek 密钥（可选）
- **特性**: 统一抽象层封装，支持流式输出（SSE）

### AKShare（A 股数据源）

- **服务**: AKShare 开源库
- **用途**: A 股行情数据、财务数据、行业分类
- **限制**: 免费接口有频率限制，实时数据存在延迟
- **策略**: 历史数据本地缓存，实时数据按需拉取

### PostgreSQL

- **用途**: 结构化数据存储（分析文章、知识库、自选股、缠论信号）
- **配置项**:
  - `DATABASE_URL`: 连接地址（格式：`postgresql://user:password@localhost:5432/ai_stock`）

### Redis

- **用途**: 缓存（行情数据、计算结果、会话）
- **配置项**:
  - `REDIS_URL`: 连接地址（格式：`redis://localhost:6379`）

### 邮件通知（可选）

- **服务**: SMTP
- **用途**: 缠论信号报警邮件通知
- **配置项**:
  - `SMTP_HOST`: SMTP 服务器地址
  - `SMTP_USER`: 发件邮箱
  - `SMTP_PASS`: SMTP 授权码

## 部署依赖

| 依赖 | 版本 | 用途 |
|------|------|------|
| Docker Compose | - | 一键编排前后端 + PostgreSQL + Redis |
| Python | 3.x | 后端运行环境 |
| Node.js | - | 前端构建环境 |

## 环境变量

```env
# 大模型配置
OPENAI_API_KEY=your_openai_key
OPENAI_BASE_URL=https://api.openai.com/v1
DEEPSEEK_API_KEY=your_deepseek_key

# 数据库
DATABASE_URL=postgresql://user:password@localhost:5432/ai_stock

# Redis
REDIS_URL=redis://localhost:6379

# 可选：邮件通知
SMTP_HOST=smtp.qq.com
SMTP_USER=your_email@qq.com
SMTP_PASS=your_smtp_password
```
