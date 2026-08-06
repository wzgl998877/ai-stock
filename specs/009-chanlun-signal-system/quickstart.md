# Quickstart: 缠论策略监控与信号回测

**Date**: 2026-08-04

## 前置确认（开发第一步，对应 research.md D1/D2）

1. **30 分钟数据源验证**：在 `backend/` 跑一段临时脚本，用 `SinaSyncClient`/`sina_kline_client` 拉取 1-2 只股票的 scale=30 历史 K，确认可拿到 ≥3 年数据、字段完整。这是全文唯一硬前置。
2. **当前 alembic head**：`cd backend && alembic heads`，记下值作为新迁移的 `down_revision`。

## 后端开发顺序

```bash
cd backend
pip install -r requirements.txt          # 无新增重依赖
cp .env.example .env                      # 填 OPENAI_API_KEY/DATABASE_URL/REDIS_URL（复用现有）
```

1. **领域层（纯函数，最先做 + 测试）**
   - `app/domain/models/chanlun_enums.py`、`app/domain/entities/chanlun.py`、`backtest.py`
   - `app/domain/services/chanlun_service.py` + `chanlun_divergence.py`
   - `tests/fixtures/chanlun_golden_samples/` + `tests/unit/domain/test_chanlun_service.py`、`test_chanlun_divergence.py`
   - **门禁**：分层黄金样本单测全绿方可继续。

2. **持久化层**
   - `app/infrastructure/db/models.py` 加 7 个 ORM 模型 → 改 `migrations/env.py` import → `alembic revision --autogenerate -m "add chanlun strategy tables"` → 检查生成文件 → `alembic upgrade head`。
   - `app/domain/repositories/chanlun_repo.py`/`backtest_repo.py`（ABC）+ `mysql_chanlun_repo.py`/`mysql_backtest_repo.py`。
   - `mysql_watchlist_repo.py` 加 `get_all_items_by_user(user_id)`。

3. **应用层**
   - `use_cases/chanlun_calc.py`（单股：读K→引擎→落库，照抄 `indicator_calc.py`）
   - `use_cases/chanlun_monitor.py`（扫描 + 重算编排）
   - `use_cases/chanlun_backtest.py`（历史重算 + 窗口收益 + 聚合）
   - `dtos/chanlun_dto.py`

4. **数据拉取扩展**
   - `sina_kline_client.py` 加 `fetch(code, period='m30')`（scale=30）。
   - 在 sync_executor 或独立函数提供 30 分钟历史回补入口（可挂到现有「数据同步」面板的数据类型里，或单独脚本）。

5. **调度与路由**
   - `infrastructure/scheduler/chanlun_scheduler.py`（日线 mon-fri 15:40；m30 八时点），在 `main.py` lifespan 注册（开关 `settings.chanlun_scan_enabled`）。
   - `routers/chanlun.py`（REST + SSE，注册到 `main.py:239-249`）。
   - `core/config.py` 加 `chanlun_*` 配置项。

6. **验证**
   ```bash
   pytest tests/unit/domain tests/integration -v
   uvicorn app.main:app --reload --port 8000
   curl http://localhost:8000/api/v1/strategy/run-status -H "X-User-Id: test"
   ```

## 前端开发顺序

```bash
cd frontend
npm install
npm run dev
```

1. `utils/marketTime.ts`（统一 `isMarketOpen`/`isTradingDay`），替换 WatchlistPage/stockDetailStore 双实现。
2. `services/strategyService.ts` + 抽 `services/sse.ts`；`domain/types.ts`/`constants.ts` 追加类型。
3. `store/strategyStore.ts`；`stockDetailStore.ts` 加 highlightDate/signalMarks/structureData。
4. `components/strategy/`（SignalBadge/StructureToggle/RecalcPanel/BacktestSummaryTable/BacktestDetailDrawer）。
5. `KLineChart.tsx` 扩展 markPoint/markLine/markArea + highlightDate 定位（补 vitest 用例）。
6. 页面：`StrategyMonitorPage`/`BacktestPage`；改 `App.tsx`/`AppLayout.tsx`（启用菜单）/`WatchlistPage`（信号列）/`StockDetailPage`（Tab + 定位）/`StockAnalysisPage`（`?code=`）。
7. 验证：
   ```bash
   npm run test    # vitest
   npm run build   # tsc 类型检查
   ```

## 黄金样本集（缠论验收，SC-003）

- 选 ≥10 只覆盖趋势上涨/下跌/大箱体盘整的历史区间。
- 由懂缠论的伙伴人工标注：顶底分型、笔、线段、中枢、各买卖点。
- 每层独立断言（允许笔对但线段错时精确定位）。
- 可选：用第三方实现（如 `chan.py`）作交叉参考，但以人工标注为唯一验收基准。

## 上线门禁清单

- [ ] 缠论分层黄金样本单测全绿（SC-003 ≥95%）
- [ ] 回测 vs 监控一致性集成测试通过（SC-005 100%）
- [ ] 收盘确认不重绘：重复计算不新增/不改写已确认信号
- [ ] 数据不足/未更新/窗口不完整 100% 界面明示（SC-007）
- [ ] 全部信号/回测处含「不构成投资建议」（FR-016）
- [ ] 后端分层无越界（Domain 不依赖 FastAPI/DB）、前端无直连 fetch
- [ ] Alembic upgrade/downgrade 双向可跑
