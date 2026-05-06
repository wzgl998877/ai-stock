"""技术指标计算服务"""

from typing import List, Tuple
from decimal import Decimal
from app.domain.entities.stock_indicator import StockIndicator


class IndicatorService:
    """技术指标计算（纯函数，不依赖外部）"""

    @staticmethod
    def calc_ma(close_prices: List[Decimal], periods: List[int] = None) -> dict:
        """计算移动平均线"""
        if periods is None:
            periods = [5, 10, 20]
        result = {}
        for period in periods:
            ma_values = []
            for i in range(len(close_prices)):
                if i < period - 1:
                    ma_values.append(None)
                else:
                    window = close_prices[i - period + 1: i + 1]
                    ma_values.append(sum(window) / Decimal(period))
            result[f"ma{period}"] = ma_values
        return result

    @staticmethod
    def calc_macd(
        close_prices: List[Decimal],
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9
    ) -> Tuple[List, List, List]:
        """计算MACD指标 (DIF, DEA, BAR)"""
        # EMA 计算
        def ema(data, period):
            result = []
            multiplier = Decimal(2) / Decimal(period + 1)
            for i, val in enumerate(data):
                if i == 0:
                    result.append(val)
                else:
                    result.append(val * multiplier + result[-1] * (1 - multiplier))
            return result

        if len(close_prices) < slow_period:
            empty = [None] * len(close_prices)
            return empty, empty, empty

        ema_fast = ema(close_prices, fast_period)
        ema_slow = ema(close_prices, slow_period)
        dif = [f - s for f, s in zip(ema_fast, ema_slow)]

        # DEA = EMA(DIF, signal_period)
        dea_raw = [d for d in dif if d is not None]
        if len(dea_raw) >= signal_period:
            dea_full = ema(dea_raw, signal_period)
            # 对齐到原始长度
            offset = len(dif) - len(dea_full)
            dea = [None] * offset + dea_full
        else:
            dea = [None] * len(dif)

        # BAR = 2 * (DIF - DEA)
        bar = []
        for d, e in zip(dif, dea):
            if d is not None and e is not None:
                bar.append(Decimal(2) * (d - e))
            else:
                bar.append(None)

        return dif, dea, bar

    @staticmethod
    def calc_kdj(
        high_prices: List[Decimal],
        low_prices: List[Decimal],
        close_prices: List[Decimal],
        n: int = 9,
        m1: int = 3,
        m2: int = 3
    ) -> Tuple[List, List, List]:
        """计算KDJ指标"""
        k_values, d_values, j_values = [], [], []
        prev_k = Decimal(50)
        prev_d = Decimal(50)

        for i in range(len(close_prices)):
            if i < n - 1:
                k_values.append(None)
                d_values.append(None)
                j_values.append(None)
                continue

            window_high = high_prices[i - n + 1: i + 1]
            window_low = low_prices[i - n + 1: i + 1]
            highest = max(window_high)
            lowest = min(window_low)

            if highest == lowest:
                rsv = Decimal(50)
            else:
                rsv = (close_prices[i] - lowest) / (highest - lowest) * Decimal(100)

            k = (Decimal(2) / Decimal(m1)) * prev_k + (Decimal(1) / Decimal(m1)) * rsv
            d = (Decimal(2) / Decimal(m2)) * prev_d + (Decimal(1) / Decimal(m2)) * k
            j = Decimal(3) * k - Decimal(2) * d

            k_values.append(k)
            d_values.append(d)
            j_values.append(j)
            prev_k = k
            prev_d = d

        return k_values, d_values, j_values

    def compute_all(
        self,
        close_prices: List[Decimal],
        high_prices: List[Decimal],
        low_prices: List[Decimal],
        trade_dates: List,
        stock_code: str,
        period: str = "daily"
    ) -> List[StockIndicator]:
        """计算所有指标并返回 StockIndicator 列表"""
        ma_result = self.calc_ma(close_prices)
        dif, dea, bar = self.calc_macd(close_prices)
        k_vals, d_vals, j_vals = self.calc_kdj(high_prices, low_prices, close_prices)

        results = []
        for i in range(len(trade_dates)):
            ma5_list = ma_result.get("ma5", [])
            ma10_list = ma_result.get("ma10", [])
            ma20_list = ma_result.get("ma20", [])

            indicator = StockIndicator(
                stock_code=stock_code,
                trade_date=trade_dates[i],
                period=period,
                ma5=ma5_list[i] if ma5_list and i < len(ma5_list) else None,
                ma10=ma10_list[i] if ma10_list and i < len(ma10_list) else None,
                ma20=ma20_list[i] if ma20_list and i < len(ma20_list) else None,
                macd_dif=dif[i],
                macd_dea=dea[i],
                macd_bar=bar[i],
                kdj_k=k_vals[i],
                kdj_d=d_vals[i],
                kdj_j=j_vals[i],
                data_source="computed",
            )
            results.append(indicator)
        return results
