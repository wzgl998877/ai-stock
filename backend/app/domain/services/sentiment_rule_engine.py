"""情感规则引擎 — 关键词匹配判断利好/利空/中性"""

POSITIVE_WORDS = [
    "涨停", "利好", "增长", "超预期", "获批", "补贴", "上调", "突破",
    "新高", "大涨", "暴涨", "翻红", "业绩大增", "订单", "中标", "扩产",
    "分红", "回购", "增持", "看好", "买入", "推荐", "升级", "加仓",
    "盈利", "复苏", "回暖", "强势", "牛市", "翻倍", "增收", "提速",
]

NEGATIVE_WORDS = [
    "跌停", "利空", "下降", "不及预期", "制裁", "限制", "下调", "违约",
    "暴跌", "大跌", "新低", "亏损", "减持", "清仓", "退市", "处罚",
    "调查", "违规", "风险", "警示", "停牌", "崩盘", "熊市", "减产",
    "裁员", "关停", "倒闭", "禁令", "封锁", "召回", "罚款", "爆雷",
]

IMPORTANCE_WORDS = ["重大", "突发", "紧急", "历史性", "罕见", "史诗级", "重磅"]


def analyze(title: str, content: str = "") -> dict:
    """分析文本情感，返回 {sentiment, confidence, importance}"""
    text = f"{title} {content}"

    pos_count = sum(1 for w in POSITIVE_WORDS if w in text)
    neg_count = sum(1 for w in NEGATIVE_WORDS if w in text)

    total = pos_count + neg_count
    if total == 0:
        sentiment = "neutral"
        confidence = 0.3
    elif pos_count > neg_count:
        sentiment = "positive"
        confidence = min(0.5 + 0.1 * (pos_count - neg_count), 0.95)
    elif neg_count > pos_count:
        sentiment = "negative"
        confidence = min(0.5 + 0.1 * (neg_count - pos_count), 0.95)
    else:
        sentiment = "neutral"
        confidence = 0.5

    importance = "low"
    if any(w in text for w in IMPORTANCE_WORDS):
        importance = "high"
    elif total >= 3:
        importance = "medium"

    return {
        "sentiment": sentiment,
        "confidence": round(confidence, 2),
        "importance": importance,
    }
