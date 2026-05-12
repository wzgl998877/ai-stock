"""事件去重服务 — URL MD5 精确去重 + Jaccard 标题去重"""

import hashlib


def url_hash(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()


def jaccard_similarity(a: str, b: str) -> float:
    """计算两个字符串的 Jaccard 相似度（基于字符集合）"""
    set_a = set(a)
    set_b = set(b)
    if not set_a and not set_b:
        return 1.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union)


def is_duplicate_title(title: str, existing_titles: list, threshold: float = 0.6) -> bool:
    """检查标题是否与已有标题重复"""
    for existing in existing_titles:
        if jaccard_similarity(title, existing) >= threshold:
            return True
    return False


def is_duplicate_url(url: str, existing_hashes: set) -> bool:
    """检查 URL 是否已存在"""
    return url_hash(url) in existing_hashes
