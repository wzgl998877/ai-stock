"""事件-股票匹配服务单元测试"""

from app.domain.services.event_stock_matcher import (
    extract_stock_codes,
    match_by_name,
    match_all,
    set_stock_name_map,
    set_industry_keywords,
)


def test_extract_stock_codes():
    text = "中国石油(601857)和宁德时代(300750)今日大涨"
    codes = extract_stock_codes(text)
    assert "601857" in codes
    assert "300750" in codes


def test_extract_stock_codes_filters_invalid():
    text = "验证码123456不是股票"
    codes = extract_stock_codes(text)
    # 123456 doesn't start with valid A-share prefix
    assert "123456" not in codes


def test_match_by_name():
    set_stock_name_map({"中国石油": "601857", "宁德时代": "300750"})
    results = match_by_name("中国石油今日涨停")
    assert len(results) >= 1
    assert any(r["code"] == "601857" for r in results)


def test_match_by_name_no_match():
    set_stock_name_map({"中国石油": "601857"})
    results = match_by_name("苹果公司发布新产品")
    assert len(results) == 0


def test_match_by_industry():
    set_industry_keywords({"石油石化": ["石油", "油价", "OPEC"]})
    from app.domain.services import event_stock_matcher
    results = event_stock_matcher.match_by_industry("国际油价突破85美元/桶")
    assert len(results) >= 1
    assert results[0]["industry"] == "石油石化"


def test_match_all_integration():
    set_stock_name_map({"宁德时代": "300750"})
    set_industry_keywords({"电力设备": ["电池", "储能"]})
    result = match_all("宁德时代(300750)储能业务增长，电池出货量创新高")
    assert len(result["stocks"]) >= 1
    assert any(s["code"] == "300750" for s in result["stocks"])
    assert len(result["industries"]) >= 1
