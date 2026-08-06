"""缠论调度器单元测试（T028）。

``setup_scheduler`` 仅注册任务、不触发执行（任务函数内才用 ``session_factory``），
故无需真实 DB 即可断言任务注册与 cron 解析。
"""

from app.infrastructure.scheduler.chanlun_scheduler import _parse_cron, setup_scheduler


def test_parse_cron():
    assert _parse_cron("15:40") == (15, 40)
    assert _parse_cron("09:05") == (9, 5)


def test_setup_registers_jobs():
    sched = setup_scheduler(session_factory=lambda: None)
    assert sched is not None
    ids = {j.id for j in sched.get_jobs()}
    assert "chanlun_daily_scan" in ids
    assert "chanlun_m30_scan" in ids


def test_m30_trigger_covers_eight_points():
    """m30 触发器应在 8 个目标时点命中（用 9:30-15:00 外不命中做反向断言）。"""
    from datetime import datetime

    sched = setup_scheduler(session_factory=lambda: None)
    m30 = next(j for j in sched.get_jobs() if j.id == "chanlun_m30_scan")

    hits = {  # 周一各时点是否命中
        (10, 5): True, (10, 35): True, (11, 5): True, (11, 35): True,
        (13, 35): True, (14, 5): True, (14, 35): True, (15, 5): True,
        (13, 5): False,   # 午休不开仓后的那一根尚未收盘
        (12, 0): False,   # 午休
        (9, 35): False,   # 早盘尚未到 10:00 第一根
        (16, 0): False,   # 收盘后
    }
    for (h, m), expected in hits.items():
        # 周一（2026-08-10）
        fire_time = datetime(2026, 8, 10, h, m)
        triggered = m30.trigger.get_next_fire_time(None, fire_time)
        # 若该时点命中，下一次触发应就在该时点（同分钟）
        if expected:
            assert triggered is not None and triggered.hour == h and triggered.minute == m, (
                f"期望 {(h, m)} 命中，实际 {triggered}"
            )
        else:
            assert triggered is None or not (triggered.hour == h and triggered.minute == m), (
                f"期望 {(h, m)} 不命中，实际命中 {triggered}"
            )
