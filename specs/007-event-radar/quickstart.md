# Quickstart: 投资事件影响雷达

**Branch**: `007-event-radar` | **Date**: 2026-05-11

## 前置条件

- 已有开发环境：Python 3.11+, Node.js 18+, MySQL, Redis
- 已有项目运行：后端 `uvicorn app.main:app`，前端 `npm run dev`
- 数据库已有基础数据（t_stock、t_industry、t_watchlist_item 等）

## 数据库迁移

```bash
# 在 backend/ 目录下执行
cd backend

# 创建迁移文件
alembic revision --autogenerate -m "add_event_radar_tables"

# 执行迁移
alembic upgrade head
```

新增 6 张表：t_impact_event, t_impact_article, t_user_impact, t_user_alert, t_morning_briefing, t_radar_config

## 后端启动

```bash
# 在 backend/ 目录下
pip install -r requirements.txt  # 确认 apscheduler 已安装

# 启动（APScheduler 在 lifespan 中自动启动）
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

启动后 APScheduler 自动注册以下定时任务：
- 交易时段（9:00-15:00 工作日）：每 10 分钟采集财经信息
- 非交易时段：每 1 小时采集
- 每天 6:30：为所有有自选股的用户生成晨报

## 前端启动

```bash
# 在 frontend/ 目录下
npm install
npm run dev
```

## 验证步骤

### 1. 验证采集管线

```bash
# 手动触发一次采集（API 触发或等待定时任务）
curl -X POST http://localhost:8000/api/v1/event-radar/admin/crawl \
  -H "Authorization: Bearer <token>"
```

检查日志输出，确认财联社或搜索引擎数据采集成功。

### 2. 验证影响面板

```bash
# 获取影响事件列表
curl http://localhost:8000/api/v1/event-radar/impacts \
  -H "Authorization: Bearer <token>"
```

打开浏览器访问 `http://localhost:5173/event-radar`，查看影响雷达面板。

### 3. 验证预警推送

如果影响判断产生了 P0/P1 事件：
```bash
# 检查未读预警
curl http://localhost:8000/api/v1/event-radar/alerts/unread-count \
  -H "Authorization: Bearer <token>"
```

前端右上角铃铛应显示未读数字。

### 4. 验证晨报

```bash
# 手动触发晨报生成（或等待 6:30 自动触发）
curl http://localhost:8000/api/v1/event-radar/briefing/today \
  -H "Authorization: Bearer <token>"
```

用户当日首次登录应弹出晨报。

### 5. 验证自选股影响徽标

打开 `http://localhost:5173/market/watchlist`，确认自选股表格新增"影响"列。

## 测试

```bash
# 后端单元测试
cd backend
pytest tests/unit/domain/test_impact_assessment.py -v
pytest tests/unit/domain/test_sentiment_rule_engine.py -v
pytest tests/unit/domain/test_event_dedup.py -v
pytest tests/unit/domain/test_event_stock_matcher.py -v

# 后端集成测试
pytest tests/integration/test_event_radar_api.py -v

# 前端测试
cd frontend
npm test
```

## 注意事项

- 财联社 API 如不可用，系统自动 fallback 到搜索引擎采集
- 首次运行需确保数据库中已有自选股数据，否则面板为空
- Redis 用于缓存预警未读数量，Redis 不可用时不影响主流程（降级为每次查数据库）
- 影响判断引擎 MVP 阶段以规则引擎为主，LLM 仅作为置信度 < 0.6 的事件兜底
