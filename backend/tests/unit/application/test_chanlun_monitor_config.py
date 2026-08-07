"""ChanlunMonitorUseCase 逐股监控配置过滤（T051）单元测试。

验证 ``scan`` 前的 ``_filter_by_config``：被用户关闭的周期对应股票应剔除，
无配置行视为默认启用，读取异常时降级为全量扫描。
"""

import pytest

from app.application.use_cases.chanlun_monitor import ChanlunMonitorUseCase
from app.domain.entities.strategy import MonitorConfig


class _FakeChanlunRepo:
    """仅需 ``get_monitor_configs`` 的最小 fake。"""

    def __init__(self, configs=None, raise_on_configs=False):
        self._configs = configs or []
        self._raise = raise_on_configs

    async def get_monitor_configs(self, user_id):
        if self._raise:
            raise RuntimeError("boom")
        return list(self._configs)


def _build_monitor(repo):
    # _filter_by_config 仅用到 chanlun_repo，其余依赖置占位（本测试不触达）
    return ChanlunMonitorUseCase(
        watchlist_repo=None,
        chanlun_repo=repo,
        algo_version="1.0.0",
        session_factory=None,
        build_calc=lambda s: None,
    )


@pytest.mark.asyncio
async def test_no_config_keeps_all():
    """无配置行 → 全部默认启用。"""
    mon = _build_monitor(_FakeChanlunRepo(configs=[]))
    kept = await mon._filter_by_config(["600000", "000001"], "daily", "u1")
    assert kept == ["600000", "000001"]


@pytest.mark.asyncio
async def test_disabled_daily_filtered_for_daily_only():
    """关闭日线 → 日线扫描剔除该股，m30 扫描仍保留。"""
    configs = [MonitorConfig(user_id="u1", stock_code="600000", daily_enabled=False, m30_enabled=True)]
    mon = _build_monitor(_FakeChanlunRepo(configs=configs))

    kept_daily = await mon._filter_by_config(["600000", "000001"], "daily", "u1")
    assert kept_daily == ["000001"]

    kept_m30 = await mon._filter_by_config(["600000", "000001"], "m30", "u1")
    assert kept_m30 == ["600000", "000001"]


@pytest.mark.asyncio
async def test_disabled_m30_filtered_for_m30_only():
    """关闭 m30 → m30 扫描剔除该股，日线扫描仍保留。"""
    configs = [MonitorConfig(user_id="u1", stock_code="000001", daily_enabled=True, m30_enabled=False)]
    mon = _build_monitor(_FakeChanlunRepo(configs=configs))

    kept_m30 = await mon._filter_by_config(["600000", "000001"], "m30", "u1")
    assert kept_m30 == ["600000"]

    kept_daily = await mon._filter_by_config(["600000", "000001"], "daily", "u1")
    assert kept_daily == ["600000", "000001"]


@pytest.mark.asyncio
async def test_read_config_failure_degrades_to_full_scan():
    """读取配置异常 → 降级全量扫描（不阻断监控）。"""
    mon = _build_monitor(_FakeChanlunRepo(raise_on_configs=True))
    kept = await mon._filter_by_config(["600000", "000001"], "daily", "u1")
    assert kept == ["600000", "000001"]


@pytest.mark.asyncio
async def test_empty_codes_passthrough():
    mon = _build_monitor(_FakeChanlunRepo(configs=[]))
    assert await mon._filter_by_config([], "daily", "u1") == []
