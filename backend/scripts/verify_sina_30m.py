"""一次性验证脚本（T022 硬前置）：确认新浪 scale=30 可拉取 30 分钟 K 线并量化实际窗口。

运行：
    cd backend && python -m scripts.verify_sina_30m [code]   # 默认 600519（贵州茅台）

验证项：
1. 拉取条数达 datalen=1500（接口单次上限，实测 1500-1999 之间，2000+ 返回空）；
2. 最早 / 最晚时间跨度量化（实测 ≈ 9 个月；接口不支持时间范围/分页，更长历史无法单次获取）；
3. 相邻两根间隔为 30 分钟（交易日时段内），时间戳为区间结束时刻；
4. 价格非负、OHLC 合理（high≥low 等）。

⚠️ 接口限制（实测）：scale=30 单次 datalen 上限 ~1500-1999 根（≈9 个月），无分页/时间范围参数。
   因此「3 年 30m 历史」单次不可达——监控每日增量 8 根可持续累积；首次回补窗口 ≈9 个月，
   30m 回测样本首次受限，日线回测仍可达 3 年。需在可访问 quotes.sina.cn 的网络环境执行。
"""

import asyncio
import sys
from datetime import datetime

from app.infrastructure.market.sina_kline_client import SinaKlineClient


def _parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts)


async def main(code: str = "600519") -> int:
    client = SinaKlineClient()
    print(f"[验证] 拉取 {code} 30分钟K线 (scale=30) ...")
    bars = await client.fetch(code, period="m30")
    if not bars:
        print("[失败] 未取到任何数据（请检查网络 / 新浪接口可用性）")
        return 1

    times = [_parse(b["trade_date"]) for b in bars if b.get("trade_date")]
    n = len(bars)
    first, last = min(times), max(times)
    span_days = (last - first).days
    span_years = span_days / 365.0

    print(f"[结果] 条数: {n}")
    print(f"[结果] 最早: {first}  最晚: {last}")
    print(f"[结果] 跨度: {span_days} 天 ≈ {span_years:.2f} 年")

    # 1. 条数门槛：实测单次上限 ~1500-1999，达 1500 即接口可用
    ok_count = n >= 1500
    print(f"[{'PASS' if ok_count else 'WARN'}] 条数≥1500 (单次上限≈1500-1999): n={n}")
    print(f"[INFO] 3年需≈6000根，但接口单次上限~1500-1999且无分页 → 3年30m历史单次不可达")

    # 3. 相邻间隔抽样（最后 20 根，应多为 30 分钟，跨日除外）
    gaps = []
    for i in range(max(1, len(times) - 20), len(times)):
        gap = (times[i] - times[i - 1]).total_seconds() / 60.0
        gaps.append(gap)
    intra = [g for g in gaps if g <= 60]
    if intra:
        ok_gap = all(20 <= g <= 35 for g in intra)
        print(f"[{'PASS' if ok_gap else 'WARN'}] 日内相邻间隔≈30min: {sorted(set(intra))}")
    else:
        print("[SKIP] 无日内相邻样本")

    # 4. OHLC 合理性抽样
    bad = 0
    for b in bars:
        o, h, l, c = b["open"], b["high"], b["low"], b["close"]
        if None in (o, h, l, c):
            continue
        if h < l or o < 0 or c < 0:
            bad += 1
    print(f"[{'PASS' if bad == 0 else 'FAIL'}] OHLC 合理（high≥low、非负）异常数: {bad}")

    print("\n[样例] 前 3 根:")
    for b in bars[:3]:
        print("  ", b)
    print("[样例] 后 3 根:")
    for b in bars[-3:]:
        print("  ", b)

    # 结论
    if ok_count and bad == 0:
        print(f"\n[结论] 接口可用，单次可拉取 {n} 根 30m K线，窗口 ≈{span_years:.2f} 年。")
        print("[提示] 监控每日增量可持续累积；首次回补窗口≈9个月，30m回测样本首次受限。")
        return 0
    print("\n[结论] 验证未通过，请复核接口/解析。")
    return 2


if __name__ == "__main__":
    code = sys.argv[1] if len(sys.argv) > 1 else "600519"
    rc = asyncio.run(main(code))
    sys.exit(rc)
