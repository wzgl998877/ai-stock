"""ILinkTokenStore 单元测试（Fake Redis 桩）。"""

import pytest

from app.infrastructure.wechat.ilink_token_store import ILinkTokenStore


class FakeRedis:
    """记录 get/set 调用的最小桩；可编程抛异常。"""

    def __init__(self, fail: bool = False):
        self.data: dict[str, str] = {}
        self.get_calls: list[str] = []
        self.set_calls: list[tuple[str, str, int]] = []
        self.fail = fail

    async def get(self, key):
        self.get_calls.append(key)
        if self.fail:
            raise ConnectionError("redis down")
        return self.data.get(key)

    async def set(self, key, value, ttl: int = 0):
        self.set_calls.append((key, value, ttl))
        if self.fail:
            raise ConnectionError("redis down")
        self.data[key] = value


@pytest.mark.asyncio
async def test_write_through_memory_and_redis():
    r = FakeRedis()
    store = ILinkTokenStore(redis=r)
    await store.set_context_token("u1", "T1")

    assert ("wechat:ilink:context_token:u1", "T1", 7 * 24 * 3600) in r.set_calls
    # 内存命中：不再查 Redis
    r.get_calls.clear()
    assert await store.get_context_token("u1") == "T1"
    assert r.get_calls == []


@pytest.mark.asyncio
async def test_redis_only_token_backfills_memory():
    """重启场景：新 store 实例从 Redis 恢复 token（读回填）。"""
    r = FakeRedis()
    r.data["wechat:ilink:context_token:u1"] = "T-OLD"
    store = ILinkTokenStore(redis=r)

    assert await store.get_context_token("u1") == "T-OLD"
    # 回填后第二次读走内存
    r.get_calls.clear()
    assert await store.get_context_token("u1") == "T-OLD"
    assert r.get_calls == []


@pytest.mark.asyncio
async def test_cursor_restart_recovery():
    r = FakeRedis()
    r.data["wechat:ilink:get_updates_buf"] = "BUF-1"
    store1 = ILinkTokenStore(redis=r)
    await store1.set_cursor("BUF-2")
    assert r.data["wechat:ilink:get_updates_buf"] == "BUF-2"

    # 模拟重启：新实例无内存，从 Redis 恢复
    store2 = ILinkTokenStore(redis=r)
    assert await store2.get_cursor() == "BUF-2"


@pytest.mark.asyncio
async def test_no_cursor_returns_empty_string():
    store = ILinkTokenStore(redis=FakeRedis())
    assert await store.get_cursor() == ""


@pytest.mark.asyncio
async def test_redis_failure_degrades_to_memory():
    """Redis 抛异常时静默降级：不向上抛，内存仍然有效。"""
    r = FakeRedis(fail=True)
    store = ILinkTokenStore(redis=r)

    # set：Redis 失败但内存写入成功
    await store.set_context_token("u1", "T1")
    await store.set_cursor("B1")
    # get：内存命中（token）/ 无内存时返回 None（cursor 因 set 失败留内存）
    assert await store.get_context_token("u1") == "T1"
    assert await store.get_cursor() == "B1"
