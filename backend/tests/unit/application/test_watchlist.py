"""WatchlistUseCase 单元测试 — 验证自选股分组管理核心业务逻辑"""

import pytest
from unittest.mock import AsyncMock, MagicMock, call

from app.application.use_cases.watchlist import WatchlistUseCase, DEFAULT_GROUP_NAME
from app.domain.entities.watchlist import WatchlistGroup, WatchlistItem


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_group(
    group_id: int = 1,
    user_id: str = "user1",
    name: str = "默认分组",
    is_default: bool = True,
    display_order: int = 0,
) -> WatchlistGroup:
    """构造一个 WatchlistGroup 实例"""
    return WatchlistGroup(
        id=group_id,
        user_id=user_id,
        name=name,
        display_order=display_order,
        is_default=is_default,
    )


def _make_item(
    item_id: int = 1,
    group_id: int = 1,
    stock_code: str = "000001",
    stock_name: str = "平安银行",
) -> WatchlistItem:
    """构造一个 WatchlistItem 实例"""
    return WatchlistItem(
        id=item_id,
        group_id=group_id,
        stock_code=stock_code,
        stock_name=stock_name,
    )


def _make_repo() -> AsyncMock:
    """构造一个全方法 AsyncMock 的 WatchlistRepository mock"""
    repo = AsyncMock()
    # 默认行为
    repo.get_groups.return_value = []
    repo.get_group_by_id.return_value = None
    repo.count_groups.return_value = 0
    repo.count_items.return_value = 0
    repo.get_items.return_value = []
    return repo


# ===========================================================================
# Test: get_groups
# ===========================================================================

class TestGetGroups:
    """get_groups 测试：获取用户分组列表"""

    @pytest.mark.anyio
    async def test_auto_creates_default_group_when_no_groups_exist(self):
        """首次访问（无分组）时自动创建默认分组"""
        repo = _make_repo()
        uc = WatchlistUseCase(repo)

        default_group = _make_group(group_id=1, name=DEFAULT_GROUP_NAME, is_default=True)

        # 第一次 get_groups 返回空 -> _ensure_default_group 创建默认分组
        # 第二次 get_groups 返回含默认分组的列表
        repo.get_groups.side_effect = [[], [default_group]]
        repo.create_group.return_value = default_group

        groups = await uc.get_groups("user1")

        # 应该调用了 create_group 来创建默认分组
        repo.create_group.assert_awaited_once()
        created = repo.create_group.call_args[0][0]
        assert created.is_default is True
        assert created.name == DEFAULT_GROUP_NAME
        assert created.user_id == "user1"

        # 最终返回的分组列表包含默认分组
        assert len(groups) == 1
        assert groups[0].name == DEFAULT_GROUP_NAME
        assert groups[0].is_default is True

    @pytest.mark.anyio
    async def test_returns_existing_groups_without_creating_new(self):
        """已有分组时直接返回，不创建新分组"""
        repo = _make_repo()
        uc = WatchlistUseCase(repo)

        group_a = _make_group(group_id=1, name=DEFAULT_GROUP_NAME, is_default=True)
        group_b = _make_group(group_id=2, name="科技股", is_default=False, display_order=1)

        # _ensure_default_group 中 get_groups 返回已有默认分组 -> 不触发创建
        # get_groups 主调用返回完整列表
        repo.get_groups.return_value = [group_a, group_b]
        repo.count_items.return_value = 5

        groups = await uc.get_groups("user1")

        # 不应调用 create_group
        repo.create_group.assert_not_awaited()

        # 返回两个分组，且 stock_count 已填充
        assert len(groups) == 2
        assert groups[0].stock_count == 5
        assert groups[1].stock_count == 5


# ===========================================================================
# Test: create_group
# ===========================================================================

class TestCreateGroup:
    """create_group 测试：创建新分组"""

    @pytest.mark.anyio
    async def test_creates_new_group_successfully(self):
        """正常创建分组"""
        repo = _make_repo()
        uc = WatchlistUseCase(repo)

        new_group = _make_group(
            group_id=3, name="新能源", is_default=False, display_order=2,
        )
        repo.count_groups.return_value = 2
        repo.create_group.return_value = new_group

        result = await uc.create_group("user1", "新能源")

        assert result.name == "新能源"
        assert result.is_default is False
        assert result.display_order == 2

        # 验证传入 create_group 的实体字段
        created = repo.create_group.call_args[0][0]
        assert created.user_id == "user1"
        assert created.name == "新能源"
        assert created.display_order == 2
        assert created.is_default is False

    @pytest.mark.anyio
    async def test_raises_error_when_name_exceeds_10_characters(self):
        """分组名称超过 10 个字符时抛出 ValueError"""
        repo = _make_repo()
        uc = WatchlistUseCase(repo)

        long_name = "这是一个非常长的分组名称"

        with pytest.raises(ValueError, match="分组名称须1-10个字符"):
            await uc.create_group("user1", long_name)

        # 不应调用 repo
        repo.create_group.assert_not_awaited()

    @pytest.mark.anyio
    async def test_raises_error_when_name_is_empty(self):
        """分组名称为空字符串时抛出 ValueError"""
        repo = _make_repo()
        uc = WatchlistUseCase(repo)

        with pytest.raises(ValueError, match="分组名称须1-10个字符"):
            await uc.create_group("user1", "")

        repo.create_group.assert_not_awaited()


# ===========================================================================
# Test: add_stock
# ===========================================================================

class TestAddStock:
    """add_stock 测试：添加股票到分组"""

    @pytest.mark.anyio
    async def test_adds_stock_to_group_successfully(self):
        """正常添加股票到分组"""
        repo = _make_repo()
        uc = WatchlistUseCase(repo)

        group = _make_group(group_id=1, user_id="user1")
        repo.get_group_by_id.return_value = group

        item = _make_item(item_id=1, group_id=1, stock_code="000001", stock_name="平安银行")
        repo.add_item.return_value = item

        result = await uc.add_stock("user1", 1, "000001", "平安银行")

        assert result.stock_code == "000001"
        assert result.stock_name == "平安银行"
        assert result.group_id == 1

        # 验证传给 add_item 的实体字段
        added = repo.add_item.call_args[0][0]
        assert added.group_id == 1
        assert added.stock_code == "000001"
        assert added.stock_name == "平安银行"

    @pytest.mark.anyio
    async def test_idempotent_adding_same_stock_twice(self):
        """幂等：重复添加同一只股票不报错"""
        repo = _make_repo()
        uc = WatchlistUseCase(repo)

        group = _make_group(group_id=1, user_id="user1")
        repo.get_group_by_id.return_value = group

        existing_item = _make_item(item_id=1, group_id=1, stock_code="000001", stock_name="平安银行")
        # add_item 实现幂等：第二次返回已有记录
        repo.add_item.return_value = existing_item

        result = await uc.add_stock("user1", 1, "000001", "平安银行")

        # 不抛异常，返回已有记录
        assert result.stock_code == "000001"
        repo.add_item.assert_awaited_once()

    @pytest.mark.anyio
    async def test_raises_error_when_group_not_found(self):
        """分组不存在时抛出 ValueError"""
        repo = _make_repo()
        uc = WatchlistUseCase(repo)
        repo.get_group_by_id.return_value = None

        with pytest.raises(ValueError, match="分组 id=999 不存在"):
            await uc.add_stock("user1", 999, "000001", "平安银行")

    @pytest.mark.anyio
    async def test_raises_error_when_user_has_no_permission(self):
        """无权操作他人分组时抛出 ValueError"""
        repo = _make_repo()
        uc = WatchlistUseCase(repo)

        # group 属于 user2，但 user1 尝试添加
        group = _make_group(group_id=1, user_id="user2")
        repo.get_group_by_id.return_value = group

        with pytest.raises(ValueError, match="无权操作此分组"):
            await uc.add_stock("user1", 1, "000001", "平安银行")


# ===========================================================================
# Test: remove_stock
# ===========================================================================

class TestRemoveStock:
    """remove_stock 测试：从分组移除股票"""

    @pytest.mark.anyio
    async def test_removes_stock_from_group(self):
        """正常移除分组中的股票"""
        repo = _make_repo()
        uc = WatchlistUseCase(repo)

        group = _make_group(group_id=1, user_id="user1")
        repo.get_group_by_id.return_value = group

        await uc.remove_stock("user1", 1, "000001")

        repo.remove_item.assert_awaited_once_with(1, "000001")

    @pytest.mark.anyio
    async def test_raises_error_when_group_not_found(self):
        """分组不存在时抛出 ValueError"""
        repo = _make_repo()
        uc = WatchlistUseCase(repo)
        repo.get_group_by_id.return_value = None

        with pytest.raises(ValueError, match="分组 id=999 不存在"):
            await uc.remove_stock("user1", 999, "000001")

    @pytest.mark.anyio
    async def test_raises_error_when_user_has_no_permission(self):
        """无权操作他人分组时抛出 ValueError"""
        repo = _make_repo()
        uc = WatchlistUseCase(repo)

        group = _make_group(group_id=1, user_id="user2")
        repo.get_group_by_id.return_value = group

        with pytest.raises(ValueError, match="无权操作此分组"):
            await uc.remove_stock("user1", 1, "000001")


# ===========================================================================
# Test: delete_group
# ===========================================================================

class TestDeleteGroup:
    """delete_group 测试：删除分组"""

    @pytest.mark.anyio
    async def test_deletes_non_default_group(self):
        """正常删除非默认分组"""
        repo = _make_repo()
        uc = WatchlistUseCase(repo)

        group = _make_group(group_id=2, name="科技股", is_default=False)
        repo.get_group_by_id.return_value = group

        await uc.delete_group(2)

        repo.delete_group.assert_awaited_once_with(2)

    @pytest.mark.anyio
    async def test_raises_error_when_deleting_default_group(self):
        """尝试删除默认分组时抛出 ValueError"""
        repo = _make_repo()
        uc = WatchlistUseCase(repo)

        group = _make_group(group_id=1, name=DEFAULT_GROUP_NAME, is_default=True)
        repo.get_group_by_id.return_value = group

        with pytest.raises(ValueError, match="默认分组不可删除"):
            await uc.delete_group(1)

        # 不应调用删除
        repo.delete_group.assert_not_awaited()

    @pytest.mark.anyio
    async def test_raises_error_when_group_not_found(self):
        """分组不存在时抛出 ValueError"""
        repo = _make_repo()
        uc = WatchlistUseCase(repo)
        repo.get_group_by_id.return_value = None

        with pytest.raises(ValueError, match="分组 id=999 不存在"):
            await uc.delete_group(999)

        repo.delete_group.assert_not_awaited()
