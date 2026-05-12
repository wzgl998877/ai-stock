"""情感规则引擎单元测试"""

from app.domain.services.sentiment_rule_engine import analyze


def test_positive_sentiment():
    result = analyze("宁德时代业绩大增，股价涨停突破新高")
    assert result["sentiment"] == "positive"
    assert result["confidence"] >= 0.5


def test_negative_sentiment():
    result = analyze("某公司暴雷，股价暴跌跌停")
    assert result["sentiment"] == "negative"
    assert result["confidence"] >= 0.5


def test_neutral_sentiment():
    result = analyze("今日大盘震荡整理")
    assert result["sentiment"] == "neutral"
    assert result["confidence"] < 0.5


def test_importance_high():
    result = analyze("突发！重大利好消息发布")
    assert result["importance"] == "high"


def test_importance_medium():
    result = analyze("市场利好利空交替，增长下降并存")
    assert result["importance"] == "medium"


def test_importance_low():
    result = analyze("日常公告发布")
    assert result["importance"] == "low"


def test_mixed_sentiment_positive():
    result = analyze("业绩增长超预期但股价下跌")
    assert result["sentiment"] == "positive"


def test_confidence_bounded():
    result = analyze("涨停利好大涨暴涨突破新高增长")
    assert result["confidence"] <= 0.95
    assert result["confidence"] >= 0.0
