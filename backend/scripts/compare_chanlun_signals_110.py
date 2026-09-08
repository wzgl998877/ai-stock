"""一次性只读对比脚本（1.1.0 口径上线前预检）：

用当前代码库的 1.1.0 引擎对自选池全部股票重算（纯函数、**不写任何表**），
与 ``t_strategy_signal`` 中已入库的 1.0.0 信号对比，回答部署前的问题：

> 「按新口径，哪些股票的现有信号会被判为不成立（错的）？」

运行：
    cd backend && python -m scripts.compare_chanlun_signals_110

对比口径：
- 键 = (signal_type, signal_time)（trigger_price 因数据重灌可能微调，不参与键）；
- 「作废」= 库中 1.0.0 有、1.1.0 重算无 → 部署重算后不再出现（含 1.0.0 行删除后即消失）；
- 「新增」= 库中无、1.1.0 重算有 → 部署首轮重算会作为新信号入库（推送端 7 天年龄过滤拦截陈旧者）；
- 「保留」= 两边都有。

注意：库里 1.0.0 信号是历史不同时点入库的，当时的 K 线与当前可能不同
（如 09-07 全量重灌），差异含数据变化影响；但 09-07 后数据已稳定，日线/
m30 对比可视为口径差异的近似。

只读保证：仅 SELECT + 引擎纯函数计算，无任何 INSERT/UPDATE/DELETE。
"""

import asyncio
import logging
from collections import defaultdict

from sqlalchemy import text as sql_text

from app.core.config import settings
from app.domain.services.chanlun_service import ChanlunService
from app.application.use_cases.chanlun_calc import ChanlunCalcUseCase
from app.domain.services.indicator_service import IndicatorService
from app.infrastructure.repositories.mysql_stock_data_repo import (
    MySQLStockDataRepository,
)
from app.core.database import async_session as session_factory

logging.basicConfig(level=logging.WARNING)

OLD_VERSION = "1.0.0"
NEW_VERSION = "1.1.0"
PERIODS = ("daily", "m30")


async def main() -> int:
    # 1) 自选池 + 库中 1.0.0 信号（一次预取）
    async with session_factory() as session:
        r = await session.execute(sql_text(
            "SELECT DISTINCT wi.stock_code FROM t_watchlist_item wi "
            "JOIN t_watchlist_group wg ON wi.group_id = wg.id "
            "WHERE wi.stock_code <> ''"
        ))
        codes = sorted({row[0] for row in r.fetchall() if row[0]})
        r2 = await session.execute(sql_text(
            "SELECT stock_code, period, signal_type, signal_time, trigger_price "
            f"FROM t_strategy_signal WHERE algo_version = '{OLD_VERSION}'"
        ))
        db_signals: dict[tuple, dict] = defaultdict(dict)
        for code, period, stype, stime, price in r2.fetchall():
            db_signals[(code, period)][(stype, stime)] = price

    print(f"自选池 {len(codes)} 只；库中 {OLD_VERSION} 信号 "
          f"{sum(len(v) for v in db_signals.values())} 条\n")

    # 2) 逐股加载 K 线（复用 UseCase 装配，含 MACD 现算与 forming 剔除）→ 纯函数重算
    calc = ChanlunCalcUseCase.__new__(ChanlunCalcUseCase)  # 只用 _load_bars，绕开落库路径
    calc.indicator_service = IndicatorService()
    report: dict[tuple, dict] = {}
    for code in codes:
        for period in PERIODS:
            try:
                async with session_factory() as session:
                    calc.stock_data_repo = MySQLStockDataRepository(session)
                    bars = await calc._load_bars(code, period)
                if not bars:
                    report[(code, period)] = {"no_data": True}
                    continue
                signals, _ = ChanlunService.compute_all(
                    bars, stock_code=code, period=period, algo_version=NEW_VERSION
                )
                new_keys = {(s.signal_type, s.signal_time): s.trigger_price for s in signals}
                old_keys = dict(db_signals.get((code, period), {}))
                report[(code, period)] = {
                    "no_data": False,
                    "kept": sorted(set(old_keys) & set(new_keys)),
                    "removed": sorted(set(old_keys) - set(new_keys)),
                    "added": sorted(set(new_keys) - set(old_keys)),
                    "old_prices": old_keys,
                    "new_prices": new_keys,
                }
            except Exception as e:
                report[(code, period)] = {"error": str(e)}

    # 3) 输出
    removed_total = added_total = kept_total = 0
    print("=" * 78)
    print(f"{'股票':<8}{'周期':<6}{'库1.0.0':>7}{'新1.1.0':>7}{'保留':>5}{'作废':>5}{'新增':>5}")
    print("-" * 78)
    for (code, period), r in sorted(report.items()):
        if r.get("no_data"):
            print(f"{code:<8}{period:<6}{'—无K线数据—':>20}")
            continue
        if r.get("error"):
            print(f"{code:<8}{period:<6}  ERROR: {r['error'][:50]}")
            continue
        n_old = len(r["kept"]) + len(r["removed"])
        n_new = len(r["kept"]) + len(r["added"])
        kept_total += len(r["kept"])
        removed_total += len(r["removed"])
        added_total += len(r["added"])
        print(f"{code:<8}{period:<6}{n_old:>7}{n_new:>7}"
              f"{len(r['kept']):>5}{len(r['removed']):>5}{len(r['added']):>5}")
    print("-" * 78)
    print(f"合计：保留 {kept_total} · 作废 {removed_total} · 新增 {added_total}")

    print("\n" + "=" * 78)
    print("作废明细（库中 1.0.0 有、1.1.0 不再报 —— 部署后这些信号消失）")
    print("-" * 78)
    for (code, period), r in sorted(report.items()):
        for stype, stime in r.get("removed", []):
            price = r["old_prices"].get((stype, stime))
            print(f"  {code} {period:<6} {stype:<6} {stime}  价 {price}")

    print("\n" + "=" * 78)
    print("新增明细（1.1.0 新挖出 —— 首轮重算入库，推送端按 7 天年龄过滤拦截陈旧者）")
    print("-" * 78)
    for (code, period), r in sorted(report.items()):
        for stype, stime in r.get("added", []):
            price = r["new_prices"].get((stype, stime))
            print(f"  {code} {period:<6} {stype:<6} {stime}  价 {price}")

    print(f"\n[口径] algo {OLD_VERSION} → {NEW_VERSION}；settings 当前 = "
          f"{settings.chanlun_algo_version}；未写库（只读 SELECT + 纯函数计算）")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
