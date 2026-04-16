"""SimilarityCalculator — jieba 分词 + Jaccard 相似度"""

import jieba
from typing import List, Set


class SimilarityCalculator:
    def __init__(self, threshold: float = 0.3):
        self.threshold = threshold

    def tokenize(self, text: str) -> Set[str]:
        """jieba 分词，返回去重词集"""
        return set(jieba.cut(text))

    def jaccard(self, set_a: Set[str], set_b: Set[str]) -> float:
        """计算 Jaccard 相似度"""
        if not set_a or not set_b:
            return 0.0
        intersection = set_a & set_b
        union = set_a | set_b
        return len(intersection) / len(union)

    def calculate(self, query: str, target: str) -> float:
        """计算两个文本的 Jaccard 相似度"""
        tokens_a = self.tokenize(query)
        tokens_b = self.tokenize(target)
        return self.jaccard(tokens_a, tokens_b)

    def is_similar(self, query: str, target: str) -> bool:
        """是否超过相似度阈值"""
        return self.calculate(query, target) >= self.threshold

    def find_similar(
        self, query: str, candidates: List[dict], top_k: int = 3,
    ) -> List[dict]:
        """
        从候选列表中找出相似度超过阈值的条目。

        candidates 格式: [{"id": ..., "title": ..., "summary": ..., "industry_tags": [...]}]
        返回格式: 原始 candidate dict 额外加入 "similarity" 字段
        """
        query_tokens = self.tokenize(query)
        results = []

        for candidate in candidates:
            # 组合标题 + 摘要 + 行业标签作为匹配目标
            target_parts = [candidate.get("title", "")]
            if candidate.get("summary"):
                target_parts.append(candidate["summary"])
            if candidate.get("industry_tags"):
                target_parts.extend(candidate["industry_tags"])

            target_text = " ".join(target_parts)
            target_tokens = self.tokenize(target_text)
            score = self.jaccard(query_tokens, target_tokens)

            if score >= self.threshold:
                results.append({**candidate, "similarity": round(score, 2)})

        # 按相似度降序，取 top_k
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:top_k]
