"""IndicatorService 单元测试

覆盖范围：
1. MA 计算：calc_ma(closes, periods) - 验证 MA5/MA10/MA20
2. MACD 计算：calc_macd(closes) - 验证 DIF/DEA/BAR
3. KDJ 计算：calc_kdj(highs, lows, closes) - 验证 K/D/J
4. 边界情况：空数据、单条数据、数据量不足以计算指标
"""

import pytest
from decimal import Decimal

from app.domain.services.indicator_service import IndicatorService


# ---------------------------------------------------------------------------
# 辅助工具
# ---------------------------------------------------------------------------

def D(val):
    """快捷创建 Decimal"""
    return Decimal(str(val))


def decimal_list(*values):
    """将一组数值转为 Decimal 列表"""
    return [Decimal(str(v)) for v in values]


def assert_decimal_close(actual, expected, tolerance=Decimal("0.0001")):
    """断言两个 Decimal 值在容差范围内相等"""
    if actual is None and expected is None:
        return
    assert actual is not None, f"期望 {expected}，实际为 None"
    assert expected is not None, f"期望 None，实际为 {actual}"
    diff = abs(actual - expected)
    assert diff <= tolerance, (
        f"数值差异过大: 实际={actual}, 期望={expected}, 差异={diff}, 容差={tolerance}"
    )


# ---------------------------------------------------------------------------
# 测试数据：模拟一只股票 30 个交易日的收盘价
# ---------------------------------------------------------------------------

CLOSE_PRICES_30 = decimal_list(
    10.00, 10.50, 11.00, 10.80, 11.20,   # 第 1-5 天
    11.50, 11.30, 11.80, 12.00, 11.70,   # 第 6-10 天
    12.10, 12.30, 12.00, 12.50, 12.80,   # 第 11-15 天
    13.00, 12.70, 13.20, 13.50, 13.30,   # 第 16-20 天
    13.60, 13.80, 14.00, 13.90, 14.20,   # 第 21-25 天
    14.50, 14.30, 14.60, 14.80, 15.00,   # 第 26-30 天
)

HIGH_PRICES_30 = decimal_list(
    10.20, 10.70, 11.20, 11.00, 11.40,
    11.80, 11.60, 12.00, 12.30, 11.90,
    12.40, 12.60, 12.30, 12.80, 13.10,
    13.30, 13.00, 13.50, 13.80, 13.60,
    13.90, 14.10, 14.30, 14.10, 14.40,
    14.80, 14.60, 14.90, 15.10, 15.20,
)

LOW_PRICES_30 = decimal_list(
    9.80, 10.20, 10.60, 10.50, 10.90,
    11.20, 11.00, 11.50, 11.70, 11.40,
    11.80, 12.00, 11.70, 12.20, 12.50,
    12.70, 12.40, 12.90, 13.20, 13.00,
    13.30, 13.50, 13.70, 13.60, 13.90,
    14.20, 14.00, 14.30, 14.50, 14.70,
)


# ===========================================================================
# 1. MA 计算
# ===========================================================================

class TestCalcMA:
    """calc_ma 测试组"""

    def test_ma5_known_values(self):
        """MA5: 用前 5 个收盘价手工验证"""
        closes = decimal_list(10.00, 10.50, 11.00, 10.80, 11.20)
        result = IndicatorService.calc_ma(closes, periods=[5])

        ma5 = result["ma5"]
        # 前 4 个不足以计算，应为 None
        assert ma5[0] is None
        assert ma5[1] is None
        assert ma5[2] is None
        assert ma5[3] is None

        # 第 5 个: (10.00 + 10.50 + 11.00 + 10.80 + 11.20) / 5 = 10.70
        expected_ma5 = (D(10.00) + D(10.50) + D(11.00) + D(10.80) + D(11.20)) / D(5)
        assert_decimal_close(ma5[4], expected_ma5)

    def test_ma5_sliding_window(self):
        """MA5: 滑动窗口验证多个位置"""
        closes = CLOSE_PRICES_30
        result = IndicatorService.calc_ma(closes, periods=[5])
        ma5 = result["ma5"]

        # 索引 4: close[0..4]
        assert_decimal_close(
            ma5[4],
            sum(closes[0:5]) / D(5),
        )

        # 索引 9: close[5..9]
        assert_decimal_close(
            ma5[9],
            sum(closes[5:10]) / D(5),
        )

        # 索引 29: close[25..29]
        assert_decimal_close(
            ma5[29],
            sum(closes[25:30]) / D(5),
        )

    def test_ma10_known_values(self):
        """MA10: 验证前 10 个数据的均值"""
        closes = CLOSE_PRICES_30
        result = IndicatorService.calc_ma(closes, periods=[10])
        ma10 = result["ma10"]

        # 前 9 个为 None
        for i in range(9):
            assert ma10[i] is None, f"ma10[{i}] 应为 None"

        # 第 10 个: sum(close[0..9]) / 10
        expected = sum(closes[0:10]) / D(10)
        assert_decimal_close(ma10[9], expected)

    def test_ma20_known_values(self):
        """MA20: 验证第 20 个数据的均值"""
        closes = CLOSE_PRICES_30
        result = IndicatorService.calc_ma(closes, periods=[20])
        ma20 = result["ma20"]

        # 前 19 个为 None
        for i in range(19):
            assert ma20[i] is None, f"ma20[{i}] 应为 None"

        # 第 20 个
        expected = sum(closes[0:20]) / D(20)
        assert_decimal_close(ma20[19], expected)

    def test_ma_default_periods(self):
        """默认 periods 参数为 [5, 10, 20]"""
        closes = CLOSE_PRICES_30
        result = IndicatorService.calc_ma(closes)

        assert "ma5" in result
        assert "ma10" in result
        assert "ma20" in result
        assert len(result) == 3

    def test_ma_custom_period(self):
        """自定义 period，如 MA3"""
        closes = decimal_list(1.00, 2.00, 3.00, 4.00, 5.00)
        result = IndicatorService.calc_ma(closes, periods=[3])
        ma3 = result["ma3"]

        assert ma3[0] is None
        assert ma3[1] is None
        # (1 + 2 + 3) / 3 = 2.0
        assert_decimal_close(ma3[2], D("2.0"))
        # (2 + 3 + 4) / 3 = 3.0
        assert_decimal_close(ma3[3], D("3.0"))
        # (3 + 4 + 5) / 3 = 4.0
        assert_decimal_close(ma3[4], D("4.0"))

    def test_ma_returns_correct_length(self):
        """MA 输出长度应与输入一致"""
        closes = decimal_list(1.00, 2.00, 3.00, 4.00, 5.00)
        result = IndicatorService.calc_ma(closes, periods=[5])
        assert len(result["ma5"]) == 5


# ===========================================================================
# 2. MACD 计算
# ===========================================================================

class TestCalcMACD:
    """calc_macd 测试组"""

    def test_macd_insufficient_data_returns_none(self):
        """数据量小于 slow_period(26) 时返回全 None"""
        closes = decimal_list(1.00, 2.00, 3.00, 4.00, 5.00)
        dif, dea, bar = IndicatorService.calc_macd(closes)

        for i in range(5):
            assert dif[i] is None, f"dif[{i}] 应为 None"
            assert dea[i] is None, f"dea[{i}] 应为 None"
            assert bar[i] is None, f"bar[{i}] 应为 None"

    def test_macd_with_enough_data(self):
        """数据量充足时，MACD 应产生有效的 Decimal 值"""
        closes = CLOSE_PRICES_30  # 30 个数据点，大于 26
        dif, dea, bar = IndicatorService.calc_macd(closes)

        # DIF 应全部为 Decimal（EMA 从第一天就开始计算）
        for i in range(len(closes)):
            assert dif[i] is not None, f"dif[{i}] 不应为 None"
            assert isinstance(dif[i], Decimal), f"dif[{i}] 应为 Decimal 类型"

        # DEA: 前 26 + 9 - 1 = 34 - 实际上 DEA 从 dif 的 EMA(signal_period) 开始
        # dif 长度 = 30, dea_raw 长度 = 30, ema(dea_raw, 9) 长度 = 30
        # 所以 offset = 0, dea 全部有值
        assert len(dif) == 30
        assert len(dea) == 30
        assert len(bar) == 30

        # 验证最后的值不是 None
        assert dif[-1] is not None
        assert dea[-1] is not None
        assert bar[-1] is not None

    def test_macd_bar_is_2_times_dif_minus_dea(self):
        """BAR = 2 * (DIF - DEA)"""
        closes = CLOSE_PRICES_30
        dif, dea, bar = IndicatorService.calc_macd(closes)

        for i in range(len(closes)):
            if dif[i] is not None and dea[i] is not None:
                expected_bar = D(2) * (dif[i] - dea[i])
                assert_decimal_close(bar[i], expected_bar)

    def test_macd_dif_is_ema_fast_minus_ema_slow(self):
        """DIF = EMA(close, 12) - EMA(close, 26)"""
        closes = CLOSE_PRICES_30
        dif, dea, bar = IndicatorService.calc_macd(closes)

        # 手工计算 EMA12 和 EMA26 来验证
        multiplier_12 = D(2) / D(13)
        multiplier_26 = D(2) / D(27)

        ema_fast = [closes[0]]
        ema_slow = [closes[0]]
        for i in range(1, len(closes)):
            ema_fast.append(closes[i] * multiplier_12 + ema_fast[-1] * (1 - multiplier_12))
            ema_slow.append(closes[i] * multiplier_26 + ema_slow[-1] * (1 - multiplier_26))

        for i in range(len(closes)):
            expected_dif = ema_fast[i] - ema_slow[i]
            assert_decimal_close(dif[i], expected_dif)

    def test_macd_custom_parameters(self):
        """自定义 fast/slow/signal 参数"""
        closes = CLOSE_PRICES_30
        dif, dea, bar = IndicatorService.calc_macd(
            closes, fast_period=6, slow_period=12, signal_period=5
        )
        # 应该正常计算，不报错
        assert len(dif) == 30
        assert dif[-1] is not None

    def test_macd_empty_data(self):
        """空数据输入"""
        dif, dea, bar = IndicatorService.calc_macd([])
        assert dif == []
        assert dea == []
        assert bar == []


# ===========================================================================
# 3. KDJ 计算
# ===========================================================================

class TestCalcKDJ:
    """calc_kdj 测试组"""

    def test_kdj_first_valid_at_index_n_minus_1(self):
        """KDJ 前 n-1（即 8）个应为 None"""
        highs = HIGH_PRICES_30
        lows = LOW_PRICES_30
        closes = CLOSE_PRICES_30

        k_vals, d_vals, j_vals = IndicatorService.calc_kdj(highs, lows, closes)

        for i in range(8):
            assert k_vals[i] is None, f"k[{i}] 应为 None"
            assert d_vals[i] is None, f"d[{i}] 应为 None"
            assert j_vals[i] is None, f"j[{i}] 应为 None"

    def test_kdj_known_values_at_index_8(self):
        """手工验证第 9 个（索引 8）KDJ 值

        使用默认 n=9, m1=3, m2=3:
        RSV = (close - lowest_low) / (highest_high - lowest_low) * 100
        K = (2/3) * prev_K + (1/3) * RSV, prev_K = 50
        D = (2/3) * prev_D + (1/3) * K, prev_D = 50
        J = 3*K - 2*D
        """
        highs = HIGH_PRICES_30
        lows = LOW_PRICES_30
        closes = CLOSE_PRICES_30

        k_vals, d_vals, j_vals = IndicatorService.calc_kdj(highs, lows, closes)

        # 窗口 [0..8]
        window_high = highs[0:9]
        window_low = lows[0:9]
        highest = max(window_high)   # 11.80
        lowest = min(window_low)     # 9.80

        rsv = (closes[8] - lowest) / (highest - lowest) * D(100)
        # closes[8] = 12.00
        # rsv = (12.00 - 9.80) / (11.80 - 9.80) * 100 = 2.20 / 2.00 * 100 = 110.0

        prev_k = D(50)
        prev_d = D(50)
        k = (D(2) / D(3)) * prev_k + (D(1) / D(3)) * rsv
        d = (D(2) / D(3)) * prev_d + (D(1) / D(3)) * k
        j = D(3) * k - D(2) * d

        assert_decimal_close(k_vals[8], k, tolerance=Decimal("0.001"))
        assert_decimal_close(d_vals[8], d, tolerance=Decimal("0.001"))
        assert_decimal_close(j_vals[8], j, tolerance=Decimal("0.001"))

    def test_kdj_j_equals_3k_minus_2d(self):
        """验证 J = 3K - 2D 的关系"""
        highs = HIGH_PRICES_30
        lows = LOW_PRICES_30
        closes = CLOSE_PRICES_30

        k_vals, d_vals, j_vals = IndicatorService.calc_kdj(highs, lows, closes)

        for i in range(len(closes)):
            if k_vals[i] is not None and d_vals[i] is not None:
                expected_j = D(3) * k_vals[i] - D(2) * d_vals[i]
                assert_decimal_close(j_vals[i], expected_j, tolerance=Decimal("0.001"))

    def test_kdj_returns_correct_length(self):
        """KDJ 输出长度应与输入一致"""
        n = 15
        highs = HIGH_PRICES_30[:n]
        lows = LOW_PRICES_30[:n]
        closes = CLOSE_PRICES_30[:n]

        k_vals, d_vals, j_vals = IndicatorService.calc_kdj(highs, lows, closes)

        assert len(k_vals) == n
        assert len(d_vals) == n
        assert len(j_vals) == n

    def test_kdj_flat_prices_rsv_is_50(self):
        """当最高价 == 最低价时，RSV 应为 50"""
        # 构造 9 天内价格完全相同的数据
        flat_val = D("10.00")
        closes = [flat_val] * 9
        highs = [flat_val] * 9
        lows = [flat_val] * 9

        k_vals, d_vals, j_vals = IndicatorService.calc_kdj(highs, lows, closes)

        # RSV = 50, prev_K = 50, prev_D = 50
        # K = 2/3 * 50 + 1/3 * 50 = 50
        # D = 2/3 * 50 + 1/3 * 50 = 50
        # J = 3*50 - 2*50 = 50
        assert_decimal_close(k_vals[8], D("50"), tolerance=Decimal("0.01"))
        assert_decimal_close(d_vals[8], D("50"), tolerance=Decimal("0.01"))
        assert_decimal_close(j_vals[8], D("50"), tolerance=Decimal("0.01"))

    def test_kdj_custom_parameters(self):
        """自定义 n, m1, m2 参数"""
        highs = HIGH_PRICES_30
        lows = LOW_PRICES_30
        closes = CLOSE_PRICES_30

        k_vals, d_vals, j_vals = IndicatorService.calc_kdj(
            highs, lows, closes, n=5, m1=2, m2=2
        )

        # n=5，前 4 个应为 None
        for i in range(4):
            assert k_vals[i] is None

        # 第 5 个（索引 4）应有值
        assert k_vals[4] is not None
        assert d_vals[4] is not None
        assert j_vals[4] is not None


# ===========================================================================
# 4. 边界情况
# ===========================================================================

class TestEdgeCases:
    """边界条件测试组"""

    def test_ma_empty_input(self):
        """空输入返回空列表"""
        result = IndicatorService.calc_ma([], periods=[5])
        assert result["ma5"] == []

    def test_ma_single_data_point(self):
        """单条数据：MA5 应为 [None]"""
        result = IndicatorService.calc_ma([D("10.00")], periods=[5])
        assert result["ma5"] == [None]

    def test_ma_exactly_period_length(self):
        """数据量刚好等于 period，应有且仅有一个有效值"""
        closes = decimal_list(1.00, 2.00, 3.00, 4.00, 5.00)
        result = IndicatorService.calc_ma(closes, periods=[5])
        ma5 = result["ma5"]

        assert ma5[0] is None
        assert ma5[1] is None
        assert ma5[2] is None
        assert ma5[3] is None
        assert_decimal_close(ma5[4], D("3.0"))

    def test_macd_single_data_point(self):
        """单条数据：MACD 应返回三个 [None]"""
        dif, dea, bar = IndicatorService.calc_macd([D("10.00")])
        assert dif == [None]
        assert dea == [None]
        assert bar == [None]

    def test_macd_exactly_slow_period(self):
        """数据量刚好等于 slow_period(26)，应能计算（>= slow_period 条件）"""
        closes = CLOSE_PRICES_30[:26]
        dif, dea, bar = IndicatorService.calc_macd(closes)

        assert len(dif) == 26
        # dif 全部有值
        assert all(d is not None for d in dif)

    def test_macd_one_less_than_slow_period(self):
        """数据量 = slow_period - 1，应返回全 None"""
        closes = CLOSE_PRICES_30[:25]
        dif, dea, bar = IndicatorService.calc_macd(closes)

        assert all(d is None for d in dif)
        assert all(d is None for d in dea)
        assert all(b is None for b in bar)

    def test_kdj_empty_input(self):
        """空输入返回三个空列表"""
        k_vals, d_vals, j_vals = IndicatorService.calc_kdj([], [], [])
        assert k_vals == []
        assert d_vals == []
        assert j_vals == []

    def test_kdj_single_data_point(self):
        """单条数据（n=9）：应为 [None]"""
        k_vals, d_vals, j_vals = IndicatorService.calc_kdj(
            [D("10.00")], [D("9.00")], [D("9.50")]
        )
        assert k_vals == [None]
        assert d_vals == [None]
        assert j_vals == [None]

    def test_kdj_exactly_n_data_points(self):
        """数据量刚好等于 n(9)，应有且仅有一个有效值"""
        highs = HIGH_PRICES_30[:9]
        lows = LOW_PRICES_30[:9]
        closes = CLOSE_PRICES_30[:9]

        k_vals, d_vals, j_vals = IndicatorService.calc_kdj(highs, lows, closes)

        # 前 8 个为 None
        for i in range(8):
            assert k_vals[i] is None
            assert d_vals[i] is None
            assert j_vals[i] is None

        # 第 9 个有值
        assert k_vals[8] is not None
        assert d_vals[8] is not None
        assert j_vals[8] is not None

    def test_kdj_one_less_than_n(self):
        """数据量 = n - 1，所有值应为 None"""
        n = 8
        highs = [D("10")] * n
        lows = [D("9")] * n
        closes = [D("9.5")] * n

        k_vals, d_vals, j_vals = IndicatorService.calc_kdj(highs, lows, closes, n=9)

        assert all(k is None for k in k_vals)
        assert all(d is None for d in d_vals)
        assert all(j is None for j in j_vals)

    def test_ma_multiple_periods_independent(self):
        """多个 period 同时计算时结果互不影响"""
        closes = decimal_list(1, 2, 3, 4, 5, 6, 7, 8, 9, 10)
        result = IndicatorService.calc_ma(closes, periods=[3, 5])

        # MA3: 索引 2 = (1+2+3)/3 = 2.0
        assert_decimal_close(result["ma3"][2], D("2.0"))
        # MA5: 索引 4 = (1+2+3+4+5)/5 = 3.0
        assert_decimal_close(result["ma5"][4], D("3.0"))

        # MA3 长度 = MA5 长度 = 10
        assert len(result["ma3"]) == 10
        assert len(result["ma5"]) == 10

    def test_macd_dea_alignment_with_short_data(self):
        """DEA 对齐：确保 dea 列表长度与 dif 一致"""
        # 使用恰好 30 个数据
        closes = CLOSE_PRICES_30
        dif, dea, bar = IndicatorService.calc_macd(closes)

        assert len(dif) == len(dea) == len(bar) == len(closes)


# ===========================================================================
# 5. compute_all 集成验证
# ===========================================================================

class TestComputeAll:
    """compute_all 方法测试组"""

    def test_compute_all_returns_stock_indicators(self):
        """compute_all 应返回 StockIndicator 列表"""
        from datetime import date
        from app.domain.entities.stock_indicator import StockIndicator

        n = 30
        closes = CLOSE_PRICES_30
        highs = HIGH_PRICES_30
        lows = LOW_PRICES_30
        dates = [date(2026, 1, i + 1) for i in range(n)]

        service = IndicatorService()
        results = service.compute_all(
            close_prices=closes,
            high_prices=highs,
            low_prices=lows,
            trade_dates=dates,
            stock_code="000001",
        )

        assert len(results) == n
        for r in results:
            assert isinstance(r, StockIndicator)
            assert r.stock_code == "000001"

        # 第一个指标的 MA5 应为 None（数据不足）
        assert results[0].ma5 is None
        # 最后一个指标的 MA5 应有值
        assert results[-1].ma5 is not None

    def test_compute_all_short_data(self):
        """数据不足时 compute_all 仍应正常运行（指标为 None）"""
        from datetime import date
        from app.domain.entities.stock_indicator import StockIndicator

        closes = decimal_list(10.00, 10.50)
        highs = decimal_list(10.20, 10.70)
        lows = decimal_list(9.80, 10.20)
        dates = [date(2026, 1, 1), date(2026, 1, 2)]

        service = IndicatorService()
        results = service.compute_all(
            close_prices=closes,
            high_prices=highs,
            low_prices=lows,
            trade_dates=dates,
            stock_code="000001",
        )

        assert len(results) == 2
        # 所有指标应为 None
        for r in results:
            assert r.ma5 is None
            assert r.ma10 is None
            assert r.ma20 is None
            assert r.kdj_k is None
