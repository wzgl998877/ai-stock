"""日线数据到位判定纯函数测试（daily_readiness）。

规则判定属 Domain 纯函数，零 mock、零 IO。基准日期（已验证星期）：
2026-09-10 周四 / 09-11 周五 / 09-12 周六 / 09-13 周日 / 09-14 周一 / 09-15 周二。
"""

from datetime import date, datetime, time

from app.domain.services.daily_readiness import (
    CLOSE_SETTLED,
    expected_daily_date,
    is_daily_data_in_place,
    judge_daily_readiness,
    parse_hhmm,
    prev_weekday,
)

D_0910, D_0911, D_0912 = date(2026, 9, 10), date(2026, 9, 11), date(2026, 9, 12)
D_0913, D_0914, D_0915 = date(2026, 9, 13), date(2026, 9, 14), date(2026, 9, 15)


# ---------------------------------------------------------------------------
# parse_hhmm / prev_weekday
# ---------------------------------------------------------------------------


def test_parse_hhmm_valid_and_fallback():
    assert parse_hhmm("15:05") == time(15, 5)
    assert parse_hhmm("08:30") == time(8, 30)
    # 非法配置回落默认（不让脏配置把扫描卡死）
    assert parse_hhmm("") == CLOSE_SETTLED
    assert parse_hhmm("abc") == CLOSE_SETTLED
    assert parse_hhmm("25:99", default=time(9, 0)) == time(9, 0)


def test_prev_weekday_skips_weekend():
    assert prev_weekday(D_0914) == D_0911   # 周一 → 上周五
    assert prev_weekday(D_0915) == D_0914   # 周二 → 周一
    assert prev_weekday(D_0912) == D_0911   # 周六 → 周五
    assert prev_weekday(D_0913) == D_0911   # 周日 → 周五


# ---------------------------------------------------------------------------
# expected_daily_date
# ---------------------------------------------------------------------------


def test_expected_date_after_close_is_today():
    assert expected_daily_date(datetime(2026, 9, 14, 15, 5)) == D_0914  # 边界：恰好就绪
    assert expected_daily_date(datetime(2026, 9, 14, 15, 40)) == D_0914
    assert expected_daily_date(datetime(2026, 9, 14, 23, 0)) == D_0914


def test_expected_date_before_close_falls_back_to_prev_weekday():
    """盘中/上午运行时期望日回退，避免每次都误判未到位而白跑重试。"""
    assert expected_daily_date(datetime(2026, 9, 14, 15, 4)) == D_0911
    assert expected_daily_date(datetime(2026, 9, 14, 9, 30)) == D_0911


def test_expected_date_weekend_is_last_weekday():
    assert expected_daily_date(datetime(2026, 9, 12, 20, 0)) == D_0911  # 周六
    assert expected_daily_date(datetime(2026, 9, 13, 20, 0)) == D_0911  # 周日


def test_expected_date_respects_custom_ready_after():
    # 就绪时刻提前到 09:35（覆盖约定俗成的当日早间数据可用场景）
    assert expected_daily_date(datetime(2026, 9, 14, 9, 40), time(9, 35)) == D_0914
    assert expected_daily_date(datetime(2026, 9, 14, 9, 30), time(9, 35)) == D_0911


# ---------------------------------------------------------------------------
# is_daily_data_in_place
# ---------------------------------------------------------------------------


def test_is_daily_data_in_place():
    assert is_daily_data_in_place(None, D_0914) is False   # 无任何数据
    assert is_daily_data_in_place(D_0911, D_0914) is False  # 落后
    assert is_daily_data_in_place(D_0914, D_0914) is True   # 恰好
    assert is_daily_data_in_place(D_0915, D_0914) is True   # 超前（不应出现，但不算未到位）


# ---------------------------------------------------------------------------
# judge_daily_readiness
# ---------------------------------------------------------------------------


def _judge(total, stale=(), failed=()):
    return judge_daily_readiness(
        total=total,
        stale_codes=list(stale),
        failed_codes=list(failed),
        expected_date=D_0914,
    )


def test_all_in_place_is_ready():
    verdict = _judge(41)
    assert verdict.ready is True
    assert verdict.should_retry is False
    assert verdict.not_in_place == 0
    assert verdict.threshold == 13          # max(2, ceil(0.3 * 41))


def test_widespread_outage_triggers_retry():
    """2026-09-14 事故形态：41 只里 38 只未到位 → 判数据源故障，等重试。"""
    verdict = _judge(41, stale=[f"c{i}" for i in range(38)])
    assert verdict.ready is False
    assert verdict.should_retry is True
    assert verdict.in_place == 3


def test_single_stale_does_not_retry():
    """孤例（疑似停牌）不触发重试——不空等，但仍如实标记未到位。"""
    verdict = _judge(41, stale=["suspended"])
    assert verdict.ready is False
    assert verdict.should_retry is False


def test_threshold_boundary_is_inclusive():
    assert _judge(41, stale=[f"c{i}" for i in range(12)]).should_retry is False
    assert _judge(41, stale=[f"c{i}" for i in range(13)]).should_retry is True


def test_failed_codes_count_toward_threshold():
    """拉取失败与「拉到了但数据旧」同等对待。"""
    verdict = _judge(41, stale=[f"s{i}" for i in range(12)], failed=["f0"])
    assert verdict.not_in_place == 13
    assert verdict.should_retry is True


def test_small_watchlist_threshold_degrades_to_total():
    """自选股只有 1-2 只时阈值退化为全部——否则 min_count 比 total 还大，永不重试。"""
    assert _judge(2, stale=["a", "b"]).should_retry is True
    assert _judge(1, stale=["a"]).should_retry is True
    assert _judge(2, stale=["a"]).should_retry is False


def test_empty_total_is_ready_and_safe():
    verdict = _judge(0)
    assert verdict.ready is True
    assert verdict.should_retry is False
    assert verdict.threshold == 0


def test_retry_codes_merges_stale_and_failed():
    verdict = _judge(41, stale=["a", "b"], failed=["c"])
    assert verdict.retry_codes == ["a", "b", "c"]
    assert verdict.stale_codes == ("a", "b")
    assert verdict.failed_codes == ("c",)
