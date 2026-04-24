# Quickstart: 多数据源股票数据体系

## 前置条件

1. MySQL 和 Redis 服务已启动
2. Python 3.11+ 环境已就绪
3. `akshare`、`tushare`、`baostock` Python 包已安装

## 环境变量配置

### 必需环境变量

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | MySQL 连接串 | `mysql+aiomysql://root:pass@localhost:3306/stock` |
| `REDIS_URL` | Redis 连接串 | `redis://localhost:6379/0` |
| `DATASOURCE_ENCRYPTION_KEY` | 数据源密钥加密 Key (Fernet 32字节 base64) | 见下方生成方法 |

### 生成加密密钥

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

将输出的密钥添加到 `.env` 文件：

```
DATASOURCE_ENCRYPTION_KEY=gAAAAAB...（完整密钥）
```

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

## 首次使用流程

### 1. 配置数据源

1. 打开应用，点击左侧导航栏「数据同步」
2. 进入「数据源配置」选项卡
3. 添加 Tushare API Token：
   - 访问 https://tushare.pro 注册并获取 Token
   - 粘贴 Token 到 API Key 输入框，点击保存
4. AKShare 无需配置，启用即可使用

### 2. 首次数据同步

1. 切换到「数据同步」选项卡
2. 选择数据源（如 Tushare）
3. 选择数据类型：
   - **基础信息**：全量股票基本信息（推荐首次同步）
   - **实时行情**：当前市场行情快照
   - **历史K线**：指定日期范围的 K 线数据
   - **财务数据**：财务报表指标
4. 点击「同步」按钮
5. 观察实时进度条，等待同步完成

### 3. 验证数据

1. 进入「个股分析」页面
2. 输入已同步的股票代码（如 000001）
3. 查看数据是否显示正常
4. 数据右上角会标注数据来源（Tushare/AKShare/BaoStock）

## 常见问题

### Redis 未启动会影响功能吗？

不会。系统会自动降级到直接查询 MySQL，仅失去缓存加速功能。

### 同步失败怎么办？

1. 检查数据源配置是否正确（特别是 Tushare Token）
2. 检查网络连接
3. 在同步历史记录中点击「重试」按钮

### 多数据源优先级是什么？

当多个数据源同时存在时，系统优先返回：Tushare > AKShare > BaoStock。

## 环境变量

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | MySQL 连接串 | Yes |
| `REDIS_URL` | Redis 连接串 | Yes |
| `DATASOURCE_ENCRYPTION_KEY` | 数据源密钥加密 Key (Fernet 32字节 base64) | Yes |
| `TUSHARE_TOKEN` | Tushare API Token (可被前端配置覆盖) | No |
