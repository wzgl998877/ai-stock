"""搜索结果值对象 — SearchResult / SearchResponse 数据类"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class SearchResult:
    """单条搜索结果"""

    title: str
    snippet: str
    url: str
    source: str
    published_date: Optional[str] = None

    def to_text(self) -> str:
        date_str = f" ({self.published_date})" if self.published_date else ""
        return f"【{self.source}】{self.title}{date_str}\n{self.snippet}"

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "snippet": self.snippet,
            "url": self.url,
            "source": self.source,
            "published_date": self.published_date,
        }

    @classmethod
    def from_dict(cls, data: dict) -> SearchResult:
        return cls(
            title=data.get("title", ""),
            snippet=data.get("snippet", ""),
            url=data.get("url", ""),
            source=data.get("source", ""),
            published_date=data.get("published_date"),
        )


@dataclass
class SearchResponse:
    """搜索响应 — 包含多条搜索结果"""

    query: str
    results: List[SearchResult] = field(default_factory=list)
    provider: str = ""
    success: bool = True
    error_message: Optional[str] = None
    search_time: float = 0.0

    def to_context(self, max_results: int = 5) -> str:
        if not self.results:
            return ""
        lines: List[str] = []
        for r in self.results[:max_results]:
            lines.append(r.to_text())
        return "\n\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "results": [r.to_dict() for r in self.results],
            "provider": self.provider,
            "success": self.success,
            "error_message": self.error_message,
            "search_time": self.search_time,
        }

    @classmethod
    def from_dict(cls, data: dict) -> SearchResponse:
        results = [SearchResult.from_dict(r) for r in data.get("results", [])]
        return cls(
            query=data.get("query", ""),
            results=results,
            provider=data.get("provider", ""),
            success=data.get("success", True),
            error_message=data.get("error_message"),
            search_time=data.get("search_time", 0.0),
        )
