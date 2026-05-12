"""事件去重服务单元测试"""

from app.domain.services.event_dedup import (
    url_hash,
    jaccard_similarity,
    is_duplicate_title,
    is_duplicate_url,
)


def test_url_hash_deterministic():
    h1 = url_hash("https://example.com/news/1")
    h2 = url_hash("https://example.com/news/1")
    assert h1 == h2
    assert len(h1) == 32


def test_url_hash_different():
    h1 = url_hash("https://example.com/news/1")
    h2 = url_hash("https://example.com/news/2")
    assert h1 != h2


def test_jaccard_identical():
    sim = jaccard_similarity("中国石油涨停", "中国石油涨停")
    assert sim == 1.0


def test_jaccard_similar():
    sim = jaccard_similarity("国际油价突破85美元", "国际油价突破90美元")
    assert sim >= 0.6


def test_jaccard_different():
    sim = jaccard_similarity("苹果发布新手机", "中石油涨停利好")
    assert sim < 0.5


def test_is_duplicate_url_found():
    h = url_hash("https://example.com/1")
    assert is_duplicate_url("https://example.com/1", {h})
    assert not is_duplicate_url("https://example.com/2", {h})


def test_is_duplicate_title_similar():
    existing = ["国际油价突破85美元/桶创三年新高"]
    assert is_duplicate_title("国际油价突破90美元/桶创三年新高", existing)
    assert not is_duplicate_title("宁德时代4月出货量同比增长35%", existing)


def test_is_duplicate_title_threshold():
    # Very different titles should not be considered duplicates
    existing = ["央行下调利率"]
    assert not is_duplicate_title("新能源汽车销量创新高", existing)
