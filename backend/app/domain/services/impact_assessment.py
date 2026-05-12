"""影响判断引擎 — 编排去重、匹配、情感分析、用户影响计算"""

from datetime import datetime
from typing import Optional

from app.domain.entities.impact_event import ImpactEvent
from app.domain.entities.user_impact import UserImpact
from app.domain.services.sentiment_rule_engine import analyze as sentiment_analyze
from app.domain.services.event_dedup import is_duplicate_url, is_duplicate_title, url_hash
from app.domain.services.event_stock_matcher import match_all, set_stock_name_map


def assess_event(
    title: str,
    content: str = "",
    source_url: str = "",
    existing_url_hashes: Optional[set] = None,
    existing_titles: Optional[list] = None,
) -> Optional[dict]:
    """评估单条新闻/事件是否值得创建为影响事件

    Returns: None（重复/无效）或 {event_data, is_new}
    """
    if not title:
        return None

    # 去重检查
    if existing_url_hashes and source_url and is_duplicate_url(source_url, existing_url_hashes):
        return None

    if existing_titles and is_duplicate_title(title, existing_titles):
        return None

    # 情感分析
    sentiment_result = sentiment_analyze(title, content)

    # 股票/行业匹配
    match_result = match_all(f"{title} {content}")

    # 只有匹配到股票或行业才值得创建事件
    if not match_result["stocks"] and not match_result["industries"]:
        return None

    return {
        "title": title,
        "summary": content[:500] if content else None,
        "sentiment": sentiment_result["sentiment"],
        "importance": sentiment_result["importance"],
        "confidence": sentiment_result["confidence"],
        "affected_stocks": match_result["stocks"],
        "affected_industries": match_result["industries"],
        "url_hash": url_hash(source_url) if source_url else None,
    }


def compute_user_impact(
    event: ImpactEvent,
    user_watchlist: list[dict],
    user_industries: Optional[list[str]] = None,
) -> Optional[UserImpact]:
    """计算事件对特定用户的影响

    Args:
        event: 影响事件
        user_watchlist: 用户自选股 [{code, name}]
        user_industries: 用户关注行业

    Returns: UserImpact 或 None（无匹配）
    """
    watchlist_codes = {s["code"] for s in user_watchlist}
    watchlist_names = {s["name"] for s in user_watchlist}

    # 匹配自选股
    matched_stocks = []
    event_stocks = event.affected_stocks or []
    for stock in event_stocks:
        code = stock.get("code", "")
        name = stock.get("name", "")
        if code in watchlist_codes or (name and name in watchlist_names):
            matched_stocks.append(stock)

    # 匹配行业
    matched_industries = []
    event_industries = event.affected_industries or []
    if user_industries:
        for ind in event_industries:
            ind_name = ind.get("name", "") if isinstance(ind, dict) else str(ind)
            if ind_name in user_industries:
                matched_industries.append(ind)

    # 无匹配则不生成 UserImpact
    if not matched_stocks and not matched_industries:
        return None

    # 计算优先级
    priority = _compute_priority(event, matched_stocks, matched_industries)

    return UserImpact(
        user_id="",  # 由调用者填充
        event_id=event.event_id or 0,
        matched_stocks=matched_stocks,
        matched_industries=matched_industries,
        priority=priority,
    )


def _compute_priority(event: ImpactEvent, stocks: list, industries: list) -> str:
    """计算影响优先级 P0/P1/P2"""
    score = 0

    # 事件重要性
    if event.importance == "high":
        score += 3
    elif event.importance == "medium":
        score += 1

    # 来源数量
    if event.source_count >= 3:
        score += 2

    # 匹配股票数
    score += min(len(stocks), 3)

    # 匹配行业数
    score += min(len(industries), 2)

    if score >= 6:
        return "P0"
    elif score >= 3:
        return "P1"
    return "P2"
