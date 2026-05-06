# Quick Start: 006-stock-detail-kline

**Feature**: 股票详情页与行情数据展示
**Branch**: `006-stock-detail-kline`

---

## 前置依赖

确保以下服务已就绪：
- MySQL 8.0+
- Redis 6.0+
- Python 3.11+（后端）
- Node.js 18+（前端）
- AKShare Python库 (`pip install akshare`)

---

## 1. 数据库初始化

### 1.1 执行 Migration

```bash
cd backend
alembic upgrade head
```

### 1.2 初始化申万行业数据

```bash
# 运行一次性数据初始化脚本
cd backend
python -m scripts.init_industry_data
```

此脚本会：
1. 从 AKShare 获取申万一级行业列表（31个）
2. 获取每行业内的股票映射关系
3. 写入 `t_industry_stock` 表
4. 更新 `t_stock` 表的 `industry_code` 和 `industry_name`

### 1.3 自选股分组自动创建

系统无登录功能，使用固定userId `"default"`。首次访问自选股页面时，后端自动为该用户创建3个默认分组（重仓股/观察股/备选股），无需migration预置。

---

## 2. 后端启动

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

验证接口：
```bash
curl http://localhost:8000/api/v1/stocks/300750
curl http://localhost:8000/api/v1/industries
```

---

## 3. 前端启动

```bash
cd frontend
npm install   # 确保 echarts 已安装
npm run dev
```

访问 `http://localhost:5173`（或实际端口）。

---

## 4. 开发顺序建议

### Phase 1A: 数据层（Day 1-2）
1. 创建 Alembic migration（新表 + 字段扩展）
2. 实现 Domain Entities（IndustryStock, WatchlistGroup, WatchlistItem, ArticleStockRelation, StockIndicator）
3. 实现 Repository Interfaces 和 MySQL 实现
4. 运行 migration 并验证表结构

### Phase 1B: 后端接口（Day 3-4）
1. 扩展 stock_data router（新增 /minute, /indicators, /detail, /search, /all）
2. 新建 watchlist router（分组CRUD + 股票增删）
3. 新建 industry router（行业列表 + 股票对比）
4. 新建 article_relation router（相关分析查询）
5. 实现技术指标计算服务（MACD, KDJ）
6. 联调测试所有接口

### Phase 1C: 前端页面（Day 5-7）
1. 扩展 StockDataService（新增所有前端接口调用）
2. 实现个股详情页（StockDetailPage）
   - 顶部价格卡组件
   - K线图组件（ECharts candlestick）
   - 周期切换组件
   - 指标开关组件
   - 底部标签页（基本信息/财务数据/同行对比/相关分析）
3. 实现侧边栏抽屉（ModuleOneDrawer）
4. 实现自选股管理页（WatchlistPage）
5. 实现行业导航页（IndustryPage）
6. 实现搜索组件（StockSearchInput）

### Phase 1D: 联动与集成（Day 8）
1. 模块一 → 模块二：StockCodeLink 点击触发侧边栏
2. 模块二 → 模块一：相关分析标签点击跳转知识库
3. 搜索组件全局可用
4. 端到端测试

---

## 5. 测试检查点

### 后端测试
- [ ] `GET /api/v1/stocks/300750` 返回正确数据结构
- [ ] `GET /api/v1/stocks/300750/minute` 返回当日分时数据
- [ ] `GET /api/v1/stocks/300750/indicators` 返回MA/MACD/KDJ
- [ ] `GET /api/v1/stocks/search?q=宁德` 返回匹配结果
- [ ] `GET /api/v1/industries/480000/stocks` 返回行业股票对比
- [ ] `POST /api/v1/watchlist/groups` 创建分组成功
- [ ] `POST /api/v1/watchlist/groups/1/stocks` 添加股票成功
- [ ] `GET /api/v1/stocks/300750/related-articles` 返回相关文章

### 前端测试
- [ ] 个股详情页加载 K 线图正常（日K默认）
- [ ] 周期切换（分时/日K/周K/月K）正常
- [ ] 指标开关（MACD/KDJ）正常显示/隐藏
- [ ] 搜索框输入"宁德"下拉显示匹配结果
- [ ] 自选股分组CRUD正常
- [ ] 行业对比表排序正常
- [ ] 模块一文章点击股票弹出侧边栏

---

## 6. 常见问题

### Q: AKShare 接口调用超时？
A: 检查网络连接；首次调用可能较慢（数据下载），后续走 Redis/MySQL 缓存。

### Q: K线图显示异常？
A: 检查 ECharts 配置中的 data 格式（须为 [open, close, low, high, volume]）；确认日期格式正确。

### Q: 技术指标计算结果与同花顺不一致？
A: 检查复权方式（默认前复权）；检查公式参数（MACD默认12,26,9；KDJ默认9,3,3）。

### Q: 自选股分组未自动创建？
A: 确认首次访问了自选股页面（触发后端自动创建逻辑）；查看 `t_watchlist_group` 表中是否存在 user_id="default" 的记录。
