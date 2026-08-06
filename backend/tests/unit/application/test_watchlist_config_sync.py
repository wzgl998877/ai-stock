"""WatchlistUseCase 自选股移除联动清理监控配置（T051）单元测试。

验证：从分组移除股票后，若该股已不在用户任何分组 → 删除逐股监控配置；
若仍存在于其他分组 → 保留配置；未注入 chanlun_repo → 不报错。
"""

import pytest

from app.application.use_cases.watchlist import WatchlistUseCase
from app.domain.entities.watchlist import WatchlistGroup, WatchlistItem


class _FakeWatchlistRepo:
    def __init__(self, group, all_items):
        self._group = group
        self._all = all_items
        self.removed = []  # 记录 remove_item 调用

    async def get_group_by_id(self, group_id):
        return self._group

    async def remove_item(self, group_id, stock_code):
        self.removed.append((group_id, stock_code))

    async def get_all_items_by_user(self, user_id):
        return list(self._all)


class _FakeChanlunRepo:
    def __init__(self):
        self.deleted = []  # 记录 delete_monitor_config 调用

    async def delete_monitor_config(self, user_id, stock_code):
        self.deleted.append((user_id, stock_code))
        return 1


def _group(group_id=1, user_id="u1"):
    return WatchlistGroup(id=group_id, user_id=user_id, name="默认", is_default=True)


@pytest.mark.asyncio
async def test_remove_deletes_config_when_stock_no_longer_in_any_group():
    """股票仅在一个分组 → 移除后联动删除监控配置。"""
    wl = _FakeWatchlistRepo(_group(), all_items=[])  # 移除后并集为空
    chanlun = _FakeChanlunRepo()
    uc = WatchlistUseCase(wl, chanlun_repo=chanlun)

    await uc.remove_stock("u1", 1, "600000")

    assert wl.removed == [(1, "600000")]
    assert chanlun.deleted == [("u1", "600000")]


@pytest.mark.asyncio
async def test_remove_keeps_config_when_stock_still_in_other_group():
    """股票仍在其他分组 → 不删除监控配置。"""
    still = [WatchlistItem(group_id=2, stock_code="600000")]
    wl = _FakeWatchlistRepo(_group(), all_items=still)
    chanlun = _FakeChanlunRepo()
    uc = WatchlistUseCase(wl, chanlun_repo=chanlun)

    await uc.remove_stock("u1", 1, "600000")

    assert wl.removed == [(1, "600000")]
    assert chanlun.deleted == []  # 仍在他组，保留配置


@pytest.mark.asyncio
async def test_remove_without_chanlun_repo_does_not_error():
    """未注入 chanlun_repo → 仅移除自选，不报错（向后兼容）。"""
    wl = _FakeWatchlistRepo(_group(), all_items=[])
    uc = WatchlistUseCase(wl, chanlun_repo=None)

    await uc.remove_stock("u1", 1, "600000")  # 不应抛异常
    assert wl.removed == [(1, "600000")]


@pytest.mark.asyncio
async def test_remove_unauthorized_group_raises():
    group = WatchlistGroup(id=1, user_id="other", name="默认", is_default=True)
    wl = _FakeWatchlistRepo(group, all_items=[])
    uc = WatchlistUseCase(wl, chanlun_repo=_FakeChanlunRepo())

    with pytest.raises(ValueError):
        await uc.remove_stock("u1", 1, "600000")
