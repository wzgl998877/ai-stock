"""缠论纯函数引擎（模块三）。

对标 ``app/domain/services/indicator_service.py`` 的纯函数风格（无 IO、不依赖
FastAPI/DB/AI），分层实现七层算法（与 ``strategy-monitor-prd-v2.md`` 「缠论算法口径」对齐）：

1. K 线包含处理 → 2. 顶底分型 → 3. 笔 → 4. 线段（特征序列法，第一种破坏）
   → 5. 中枢 [ZD,ZG] → 6. 背驰（``chanlun_divergence``） → 7. 一/二/三类买卖点

输入：``list[KlineBar]``（OHLCV + ``macd_bar``，由 UseCase 注入）；
输出：``(list[ChanlunSignal], StructureSnapshot)``。

⚠️ 收盘确认不重绘：引擎接收的必须是**已剔除未收盘 K 线**的序列（UseCase 职责）；
同一输入恒等输出（确定性），重复计算不新增信号（幂等由 UseCase + ``dedup_key`` 保证）。
"""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from typing import Optional

from app.domain.entities.chanlun import (
    Bi,
    ChanlunSignal,
    Direction,
    Fractal,
    FractalType,
    KlineBar,
    Segment,
    StructureSnapshot,
    Zhongshu,
)
from app.domain.services.chanlun_divergence import detect_divergence

# 算法版本（与 ``settings.chanlun_algo_version`` 默认值一致；UseCase 落库时以配置为准）
ALGO_VERSION = "1.0.0"

# 笔的最小独立 K 线数（含包含处理后）
MIN_BI_KLINES = 5
# 线段最少笔数
MIN_SEGMENT_BIS = 3


class ChanlunService:
    """缠论算法引擎（纯函数）。"""

    # ------------------------------------------------------------------
    # 1. K 线包含处理
    # ------------------------------------------------------------------

    @staticmethod
    def process_inclusion(bars: list[KlineBar]) -> list[KlineBar]:
        """K 线包含处理：相邻 K 线若互相包含则按方向合并，返回合并后的序列。

        合并方向由前一非包含 K 决定：上升方向取 ``max(high)/max(low)``，
        下降方向取 ``min(high)/min(low)``。合并后重排 ``index`` 为连续下标。
        不修改输入对象（用 ``dataclasses.replace`` 构造副本）。
        """
        if len(bars) < 2:
            return [replace(b) for b in bars]

        result: list[KlineBar] = [replace(bars[0])]
        for cur in bars[1:]:
            last = result[-1]
            a_includes_b = last.high >= cur.high and last.low <= cur.low
            b_includes_a = cur.high >= last.high and cur.low <= last.low
            if a_includes_b or b_includes_a:
                # 确定合并方向
                if len(result) >= 2:
                    prev2 = result[-2]
                    if last.high > prev2.high:
                        direction: str = "up"
                    elif last.low < prev2.low:
                        direction = "down"
                    else:
                        direction = "up" if cur.close >= last.close else "down"
                else:
                    direction = "up" if cur.close >= last.close else "down"

                if direction == "up":
                    new_high = max(last.high, cur.high)
                    new_low = max(last.low, cur.low)
                else:
                    new_high = min(last.high, cur.high)
                    new_low = min(last.low, cur.low)

                merged = replace(
                    last,
                    high=new_high,
                    low=new_low,
                    close=cur.close,
                    volume=(last.volume or Decimal(0)) + (cur.volume or Decimal(0)),
                    macd_bar=cur.macd_bar if cur.macd_bar is not None else last.macd_bar,
                )
                result[-1] = merged
            else:
                result.append(replace(cur))

        for i, b in enumerate(result):
            b.index = i
        return result

    # ------------------------------------------------------------------
    # 2. 顶底分型
    # ------------------------------------------------------------------

    @staticmethod
    def find_fractals(bars: list[KlineBar]) -> list[Fractal]:
        """在包含处理后序列上找顶/底分型，并合并连续同向分型（保留极值最远者）。"""
        fractals: list[Fractal] = []
        n = len(bars)
        for i in range(1, n - 1):
            prev_b, cur_b, nxt_b = bars[i - 1], bars[i], bars[i + 1]
            if (
                cur_b.high > prev_b.high
                and cur_b.high > nxt_b.high
                and cur_b.low > prev_b.low
                and cur_b.low > nxt_b.low
            ):
                fractals.append(Fractal(FractalType.TOP, i, cur_b.high, cur_b.time))
            elif (
                cur_b.low < prev_b.low
                and cur_b.low < nxt_b.low
                and cur_b.high < prev_b.high
                and cur_b.high < nxt_b.high
            ):
                fractals.append(Fractal(FractalType.BOTTOM, i, cur_b.low, cur_b.time))
        return ChanlunService._merge_consecutive_fractals(fractals)

    @staticmethod
    def _merge_consecutive_fractals(fractals: list[Fractal]) -> list[Fractal]:
        """合并连续同向分型：同向相邻时取极值（顶取高、底取低），保证严格方向交替。"""
        if not fractals:
            return []
        merged: list[Fractal] = [fractals[0]]
        for f in fractals[1:]:
            last = merged[-1]
            if f.type == last.type:
                if f.type == FractalType.TOP:
                    if f.price > last.price:
                        merged[-1] = f
                else:
                    if f.price < last.price:
                        merged[-1] = f
            else:
                merged.append(f)
        return merged

    # ------------------------------------------------------------------
    # 3. 笔
    # ------------------------------------------------------------------

    @staticmethod
    def build_bis(fractals: list[Fractal], bars: list[KlineBar]) -> list[Bi]:
        """构建笔：相邻不同向分型连线。

        ``kline_count >= MIN_BI_KLINES`` 为已确认笔（``confirmed=True``）；
        否则为未确认（``confirmed=False``），不参与线段/中枢/信号。
        """
        bis: list[Bi] = []
        if len(fractals) < 2:
            return bis
        for i in range(1, len(fractals)):
            start, end = fractals[i - 1], fractals[i]
            kline_count = end.kline_index - start.kline_index + 1
            direction = Direction.DOWN if start.type == FractalType.TOP else Direction.UP
            confirmed = kline_count >= MIN_BI_KLINES
            bis.append(Bi(direction, start, end, kline_count, confirmed=confirmed))
        return bis

    # ------------------------------------------------------------------
    # 4. 线段（特征序列法，第一种破坏的实用近似）
    # ------------------------------------------------------------------

    @staticmethod
    def build_segments(bis: list[Bi]) -> list[Segment]:
        """构建线段：由 ≥3 笔组成；反向笔突破线段极值即第一种破坏，线段结束。

        注：严格缠论线段使用特征序列分型（第一/第二种破坏）。本实现为「主流实用近似」：
        当反向笔的终点跌破（上涨线段）/升破（下跌线段）线段运行以来的最低/高点时，
        判定线段结束。该口径可测、确定，上线前由懂缠论的伙伴对照样本校准。
        """
        cb = [b for b in bis if b.confirmed]
        if len(cb) < MIN_SEGMENT_BIS:
            return []

        segments: list[Segment] = []
        seg_dir = cb[0].direction
        seg_start = cb[0].start
        last_end = cb[0].end
        count = 1
        extreme_high = max(cb[0].start.price, cb[0].end.price)
        extreme_low = min(cb[0].start.price, cb[0].end.price)

        for i in range(1, len(cb)):
            bi = cb[i]
            ehigh = max(bi.start.price, bi.end.price)
            elow = min(bi.start.price, bi.end.price)

            # 先用「截至上一笔」的极值判断是否破坏，再纳入当前笔更新极值
            destroyed = False
            if bi.direction != seg_dir:
                if seg_dir == Direction.UP and bi.end.price < extreme_low:
                    destroyed = True
                elif seg_dir == Direction.DOWN and bi.end.price > extreme_high:
                    destroyed = True

            extreme_high = max(extreme_high, ehigh)
            extreme_low = min(extreme_low, elow)

            if destroyed and count >= MIN_SEGMENT_BIS:
                segments.append(
                    Segment(seg_dir, seg_start, last_end, count, confirmed=True, break_type="first")
                )
                seg_dir = bi.direction
                seg_start = last_end
                last_end = bi.end
                count = 1
                extreme_high = max(seg_start.price, bi.end.price)
                extreme_low = min(seg_start.price, bi.end.price)
            else:
                last_end = bi.end
                count += 1

        if count >= MIN_SEGMENT_BIS:
            segments.append(Segment(seg_dir, seg_start, last_end, count, confirmed=True))
        return segments

    # ------------------------------------------------------------------
    # 5. 中枢
    # ------------------------------------------------------------------

    @staticmethod
    def find_zhongshu(bis: list[Bi]) -> list[Zhongshu]:
        """识别中枢：至少连续三笔的重叠区间 [ZD, ZG]，后续与区间相交的笔纳入扩展。

        ZG = min(第 1、2 笔高点)；ZD = max(第 1、2 笔低点)；ZG≥ZD 方成形。
        GG/DD 为中枢内最高/最低点。后续笔一旦与 [ZD,ZG] 不相交则中枢结束。
        """
        cb = [b for b in bis if b.confirmed]
        result: list[Zhongshu] = []
        n = len(cb)
        i = 0
        while i + 2 < n:
            b1, b2, b3 = cb[i], cb[i + 1], cb[i + 2]
            h1 = max(b1.start.price, b1.end.price)
            l1 = min(b1.start.price, b1.end.price)
            h2 = max(b2.start.price, b2.end.price)
            l2 = min(b2.start.price, b2.end.price)
            zg = min(h1, h2)
            zd = max(l1, l2)
            if zg >= zd:
                h3 = max(b3.start.price, b3.end.price)
                l3 = min(b3.start.price, b3.end.price)
                gg = max(h1, h2, h3)
                dd = min(l1, l2, l3)
                j = i + 2
                while j + 1 < n:
                    nh = max(cb[j + 1].start.price, cb[j + 1].end.price)
                    nl = min(cb[j + 1].start.price, cb[j + 1].end.price)
                    if nl <= zg and nh >= zd:
                        gg = max(gg, nh)
                        dd = min(dd, nl)
                        j += 1
                    else:
                        break
                result.append(
                    Zhongshu(
                        zg=zg, zd=zd, gg=gg, dd=dd,
                        enter_time=b1.start.time, exit_time=cb[j].end.time,
                        enter_index=i, state="ended",
                    )
                )
                i = j + 1
            else:
                i += 1
        return result

    # ------------------------------------------------------------------
    # 6 & 7. 买卖点 + 组装入口
    # ------------------------------------------------------------------

    @staticmethod
    def compute_all(
        bars: list[KlineBar],
        stock_code: str,
        period: str,
        algo_version: str = ALGO_VERSION,
    ) -> tuple[list[ChanlunSignal], StructureSnapshot]:
        """完整计算：包含 → 分型 → 笔 → 线段 → 中枢 → 背驰 → 买卖点。

        Returns:
            (signals, snapshot)。``bars`` 不足时返回空信号与空结构快照。
        """
        snapshot = StructureSnapshot(stock_code=stock_code, period=period, algo_version=algo_version)
        if len(bars) < MIN_BI_KLINES:
            return [], snapshot

        processed = ChanlunService.process_inclusion(bars)
        fractals = ChanlunService.find_fractals(processed)
        bis = ChanlunService.build_bis(fractals, processed)
        segments = ChanlunService.build_segments(bis)
        zhongshu = ChanlunService.find_zhongshu(bis)

        snapshot.strokes = [b for b in bis if b.confirmed]
        snapshot.segments = segments
        snapshot.zhongshu = zhongshu
        # 水位线取原始输入末根（而非包含合并后序列末根）：合并保留组首 time，
        # 末根被吞时 processed[-1].time 早于库中最新 K 线 → 与监控层
        # _is_stale 的比较口径（库中最新未合并 K 线）永不相等，该股每次
        # 扫描都被判"有新数据"空转重算（2026-09-02 生产：17/37 只 m30、
        # 13/37 只日线长年空转，重算后水位仍停在合并组起点）
        snapshot.last_kline_time = bars[-1].time if bars else None
        snapshot.algo_version = algo_version

        signals = ChanlunService._detect_signals(
            processed, bis, segments, zhongshu, stock_code, period, algo_version
        )
        return signals, snapshot

    @staticmethod
    def _detect_signals(
        bars: list[KlineBar],
        bis: list[Bi],
        segments: list[Segment],
        zhongshu: list[Zhongshu],
        stock_code: str,
        period: str,
        algo_version: str,
    ) -> list[ChanlunSignal]:
        """识别一/二/三类买卖点。

        - 一类：相邻同向线段，后者创新极值且背驰 → 趋势末端转折。
        - 二类：一类之后的第一次反向回调不破一类点 → 回调底/顶。
        - 三类：中枢突破后回踩不进中枢 → 回踩底/顶。

        ``confirmed_at`` = 理论最早确认时刻：信号依赖的确认分型，其右肩 K 线
        （包含处理后序列 ``bars[end_idx + 1]``）的收盘时刻——分型须有右侧 K
        线才能成立（``find_fractals``），尾盘信号的右肩要到下一根 K 线收盘才
        出现，故 ``confirmed_at`` 常晚于 ``signal_time``。
        """
        signals: list[ChanlunSignal] = []
        cb = [b for b in bis if b.confirmed]

        def _add(signal_type: str, when, price: Decimal, end_idx: Optional[int] = None) -> None:
            # 分型必有右肩 K 线（否则 find_fractals 不产出），end_idx+1 越界仅防御
            confirmed = (
                bars[end_idx + 1].time
                if end_idx is not None and end_idx + 1 < len(bars)
                else when
            )
            signals.append(
                ChanlunSignal(
                    stock_code=stock_code,
                    period=period,
                    signal_type=signal_type,
                    structure_level="segment",
                    signal_time=when,
                    confirmed_at=confirmed,
                    trigger_price=price,
                    algo_version=algo_version,
                    status="confirmed",
                )
            )

        # --- 一类买卖点（线段背驰转折） ---
        down_segs = [s for s in segments if s.direction == Direction.DOWN]
        for k in range(1, len(down_segs)):
            prev_s, curr_s = down_segs[k - 1], down_segs[k]
            if curr_s.end.price < prev_s.end.price and detect_divergence(
                bars,
                prev_s.start.kline_index, prev_s.end.kline_index,
                curr_s.start.kline_index, curr_s.end.kline_index,
                Direction.DOWN,
            ):
                _add("buy1", curr_s.end.time, curr_s.end.price, curr_s.end.kline_index)

        up_segs = [s for s in segments if s.direction == Direction.UP]
        for k in range(1, len(up_segs)):
            prev_s, curr_s = up_segs[k - 1], up_segs[k]
            if curr_s.end.price > prev_s.end.price and detect_divergence(
                bars,
                prev_s.start.kline_index, prev_s.end.kline_index,
                curr_s.start.kline_index, curr_s.end.kline_index,
                Direction.UP,
            ):
                _add("sell1", curr_s.end.time, curr_s.end.price, curr_s.end.kline_index)

        # --- 二类买卖点（一类后回调不破一类点） ---
        for sig in list(signals):
            anchor_idx = ChanlunService._fractal_index_at(cb, sig.signal_time, sig.trigger_price)
            if anchor_idx is None:
                continue
            if sig.signal_type == "buy1":
                # 找一类买之后的第一个向下笔（回调），其终点不破一类买价
                for bi in cb:
                    if bi.direction != Direction.DOWN:
                        continue
                    if bi.end.kline_index > anchor_idx and bi.end.price > sig.trigger_price:
                        _add("buy2", bi.end.time, bi.end.price, bi.end.kline_index)
                        break
            elif sig.signal_type == "sell1":
                for bi in cb:
                    if bi.direction != Direction.UP:
                        continue
                    if bi.end.kline_index > anchor_idx and bi.end.price < sig.trigger_price:
                        _add("sell2", bi.end.time, bi.end.price, bi.end.kline_index)
                        break

        # --- 三类买卖点（中枢突破回踩不进中枢） ---
        for zs in zhongshu:
            exit_idx = ChanlunService._kline_index_after(zs, cb)
            if exit_idx is None:
                continue
            for bi in cb:
                if bi.end.kline_index <= exit_idx:
                    continue
                # 向上突破 ZG 后回踩不破 ZG
                if bi.direction == Direction.UP and bi.end.price > zs.zg:
                    # 找紧随其后的向下回调笔
                    nxt = ChanlunService._next_bi(cb, bi)
                    if nxt is not None and nxt.direction == Direction.DOWN and nxt.end.price > zs.zg:
                        _add("buy3", nxt.end.time, nxt.end.price, nxt.end.kline_index)
                        break
                # 向下跌破 ZD 后反弹不进 ZD
                if bi.direction == Direction.DOWN and bi.end.price < zs.zd:
                    nxt = ChanlunService._next_bi(cb, bi)
                    if nxt is not None and nxt.direction == Direction.UP and nxt.end.price < zs.zd:
                        _add("sell3", nxt.end.time, nxt.end.price, nxt.end.kline_index)
                        break

        # 多中枢可能在同一根 K 线回踩触发同类买卖点（buy3/sell3）；同位置信号视为
        # 同一事件，按 (signal_type, signal_time) 去重并保留首次出现——与
        # make_dedup_key 语义一致、满足 test_no_duplicate_signal_at_same_position 不变量。
        seen: set = set()
        deduped: list[ChanlunSignal] = []
        for s in signals:
            pos = (s.signal_type, s.signal_time)
            if pos in seen:
                continue
            seen.add(pos)
            deduped.append(s)
        signals = deduped

        signals.sort(key=lambda s: s.signal_time)
        return signals

    # ------------------------------------------------------------------
    # 小工具
    # ------------------------------------------------------------------

    @staticmethod
    def _fractal_index_at(cb: list[Bi], when, price: Optional[Decimal]) -> Optional[int]:
        """在已确认笔中找到匹配 (time≈when, price≈price) 的端点分型下标。"""
        for bi in cb:
            for fr in (bi.start, bi.end):
                if fr.time == when and fr.price == price:
                    return fr.kline_index
        return None

    @staticmethod
    def _kline_index_after(zs: Zhongshu, cb: list[Bi]) -> Optional[int]:
        """中枢出口之后的起始分型下标。"""
        if zs.enter_index + 1 < len(cb):
            return cb[min(zs.enter_index + 1, len(cb) - 1)].end.kline_index
        return None

    @staticmethod
    def _next_bi(cb: list[Bi], bi: Bi) -> Optional[Bi]:
        """返回 ``bi`` 在已确认笔序列中的下一笔。"""
        for i, b in enumerate(cb):
            if b is bi and i + 1 < len(cb):
                return cb[i + 1]
        return None
