# Quickstart: 多数据源股票数据体系

## 前置条件

1. MongoDB/MySQL 和 Redis 服务已启动
2. Python 3.11+ 环境已就绪
3. `akshare`、`tushare`、`baostock` Python 包已安装

## 后端启动

```bash
cd backend

# 安装依赖 (含新增数据源包)
pip install -r requirements.txt

# 数据库迁移 (新增数据源相关表)
alembic upgrade head

# 启动服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 前端启动

```bash
cd frontend

npm install

npm run dev
```

## 首次配置

1. 访问应用页面，进入数据源配置
2. 添加 Tushare API Token（从 https://tushare.pro 获取）
3. AKShare 无需配置，启用即可使用
4. BaoStock 需先注册账号

## 使用流程

1. 打开同步侧边栏（页面右侧滑入）
2. 选择数据源（如 Tushare）和数据类型（如股票基础信息）
3. 点击"同步"按钮
4. 观察实时进度条
5. 同步完成后，在个股分析页面验证数据

## 环境变量

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | MySQL 连接串 | Yes |
| `REDIS_URL` | Redis 连接串 | Yes |
| `DATASOURCE_ENCRYPTION_KEY` | 数据源密钥加密 Key (Fernet 32字节 base64) | Yes |
| `TUSHARE_TOKEN` | Tushare API Token (可被前端配置覆盖) | No |
