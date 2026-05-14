"""事件-股票匹配服务 — 三级匹配：正则→名称→行业关键词"""

import re
from typing import Optional


# A股代码正则
STOCK_CODE_RE = re.compile(r"(?<![0-9])(\d{6})(?![0-9])")

# 常见名称-代码映射（运行时从数据库/缓存加载）
_stock_name_map: Optional[dict] = None

# 行业关键词映射
INDUSTRY_KEYWORDS: dict[str, list[str]] = {}


def set_stock_name_map(name_map: dict):
    """注入股票名称映射 {name: code}"""
    global _stock_name_map
    _stock_name_map = name_map


def set_industry_keywords(mapping: dict):
    """注入行业关键词映射 {industry_name: [keywords]}"""
    global INDUSTRY_KEYWORDS
    INDUSTRY_KEYWORDS = mapping


def extract_stock_codes(text: str) -> list[str]:
    """第一级：正则提取 A 股代码"""
    matches = STOCK_CODE_RE.findall(text)
    # 过滤有效代码范围
    valid = []
    for code in matches:
        if code.startswith(("6", "0", "3", "688", "8")):
            valid.append(code)
    return list(set(valid))


def match_by_name(text: str) -> list[dict]:
    """第二级：名称模糊匹配"""
    if not _stock_name_map:
        return []
    results = []
    for name, code in _stock_name_map.items():
        if len(name) >= 2 and name in text:
            results.append({"code": code, "name": name, "match_type": "name"})
    return results


def match_by_industry(text: str) -> list[dict]:
    """第三级：行业关键词匹配"""
    results = []
    for industry, keywords in INDUSTRY_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                results.append({"industry": industry, "keyword": kw, "match_type": "industry"})
                break
    return results


def match_all(text: str) -> dict:
    """执行三级匹配，返回 {stocks: [{code, name, match_type}], industries: [{industry, keyword}]}"""
    # 第一级：正则
    code_stocks = [{"code": c, "name": "", "match_type": "regex"} for c in extract_stock_codes(text)]

    # 第二级：名称
    name_stocks = match_by_name(text)

    # 合并去重（以 code 为准，优先保留有名称的匹配）
    stock_by_code: dict[str, dict] = {}
    for s in code_stocks + name_stocks:
        code = s.get("code", "")
        if not code:
            continue
        existing = stock_by_code.get(code)
        if existing is None or (not existing.get("name") and s.get("name")):
            stock_by_code[code] = s
    all_stocks = list(stock_by_code.values())

    # 第三级：行业
    industries = match_by_industry(text)

    return {"stocks": all_stocks, "industries": industries}
