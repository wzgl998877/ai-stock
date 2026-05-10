"""统一搜索服务 — 多引擎故障转移 + 中文优先 + 时效过滤 + Redis 缓存"""

import hashlib
import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from app.domain.value_objects.search_result import SearchResult, SearchResponse
from app.infrastructure.search.base_provider import BaseSearchProvider
from app.infrastructure.search.cache import SearchCache
from app.core.config import settings

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# 常量
# ──────────────────────────────────────────────

NEWS_STRATEGY_WINDOWS = {
    "ultra_short": 1,
    "short": 3,
    "medium": 7,
    "long": 30,
}

_INTEL_QUERIES = {
    "latest_news": "{name} 最新新闻",
    "market_analysis": "{name} 市场分析 机构评级",
    "risk_check": "{name} 风险 预警 负面",
    "announcements": "{name} 公告",
    "earnings": "{name} 财报 业绩",
    "industry": "{name} 行业 板块",
}

# 中文检测
_CJK_PATTERN = re.compile(r"[\u4e00-\u9fff]")
# 日期格式列表
_DATE_FORMATS = [
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
    "%Y/%m/%d %H:%M:%S",
    "%Y/%m/%d",
    "%Y年%m月%d日",
    "%d %B %Y",
    "%B %d, %Y",
    "%b %d, %Y",
    "%d-%m-%Y",
    "%m/%d/%Y",
    "%Y.%m.%d",
]

# 相对时间正则
_RELATIVE_CN = re.compile(
    r"(?:(\d+)\s*天前)|(?:(\d+)\s*小时前)|(?:(\d+)\s*分钟前)|"
    r"(今天|昨天|前天)"
)
_RELATIVE_EN = re.compile(
    r"(?:(\d+)\s*days?\s*ago)|(?:(\d+)\s*hours?\s*ago)|"
    r"(?:(\d+)\s*minutes?\s*ago)|(today|yesterday)"
)


# ──────────────────────────────────────────────
# 辅助函数
# ──────────────────────────────────────────────

def normalize_news_strategy_profile(profile: str) -> str:
    """归一化新闻窗口策略名称。"""
    p = profile.lower().strip().replace("-", "_").replace(" ", "_")
    if p in NEWS_STRATEGY_WINDOWS:
        return p
    return "short"


def resolve_news_window_days(profile: str, fallback_days: int = 3) -> int:
    """根据策略名返回天数窗口。"""
    key = normalize_news_strategy_profile(profile)
    return NEWS_STRATEGY_WINDOWS.get(key, fallback_days)


# ──────────────────────────────────────────────
# SearchService
# ──────────────────────────────────────────────

class SearchService:
    """统一搜索服务。"""

    def __init__(
        self,
        providers: List[BaseSearchProvider],
        cache: SearchCache,
    ) -> None:
        self._providers = providers
        self._cache = cache

    @property
    def is_available(self) -> bool:
        return any(p.is_available for p in self._providers)

    # ------------------------------------------------------------------
    # 公开 API
    # ------------------------------------------------------------------

    async def search(
        self,
        query: str,
        max_results: int = 5,
        days: int = 7,
        **kwargs: Any,
    ) -> SearchResponse:
        """通用搜索 — 按优先级取第一个可用引擎。"""
        for provider in self._providers:
            if not provider.is_available:
                continue
            response = await provider.search(query, max_results, days, **kwargs)
            if response.success and response.results:
                return response
        return SearchResponse(
            query=query, success=False,
            error_message="所有搜索引擎不可用",
        )

    async def search_stock_news(
        self,
        stock_code: str,
        stock_name: str = "",
        max_results: int = 5,
        focus_keywords: Optional[List[str]] = None,
    ) -> SearchResponse:
        """股票新闻搜索 — 多引擎故障转移 + 中文优先 + 时效过滤 + 缓存。"""
        # 构建查询
        name_part = stock_name or stock_code
        query = f"{name_part} 最新新闻"
        if focus_keywords:
            query = f"{name_part} {' '.join(focus_keywords[:3])}"

        prefer_chinese = self._should_prefer_chinese_news(stock_code)
        search_days = resolve_news_window_days(
            getattr(settings, "news_strategy_profile", "short"),
            fallback_days=getattr(settings, "news_max_age_days", 3),
        )
        provider_max = self._provider_request_size(max_results)

        # 缓存检查
        cache_key = self._cache_key(query, max_results, search_days, prefer_chinese)
        cached = await self._cache.get(cache_key)
        if cached is not None:
            logger.info("[SearchService] 缓存命中: %s", query[:50])
            return cached

        # 防击穿：尝试获取锁
        lock_acquired = await self._cache.acquire_lock(cache_key)
        if not lock_acquired:
            # 其他协程正在填充，等待结果
            waited = await self._cache.wait_for_fill(cache_key)
            if waited is not None:
                return waited
            # 等超时，放行本次请求
            lock_acquired = True

        try:
            # 多引擎故障转移
            best_response: Optional[SearchResponse] = None
            best_preferred_count = 0

            for provider in self._providers:
                if not provider.is_available:
                    continue

                search_kwargs: Dict[str, Any] = {}
                if provider.name == "Tavily":
                    search_kwargs["topic"] = "news"

                response = await provider.search(query, provider_max, search_days, **search_kwargs)
                filtered = self._filter_news_response(response, search_days)

                if not filtered.success or not filtered.results:
                    continue

                if not prefer_chinese:
                    best_response = filtered
                    break

                # 中文优先：比较各引擎中文结果数
                prioritized, preferred_count = self._prioritize_news_language(filtered, prefer_chinese)
                if preferred_count > best_preferred_count:
                    best_preferred_count = preferred_count
                    best_response = prioritized

            if best_response is None:
                return SearchResponse(
                    query=query, success=False,
                    error_message="所有搜索引擎未返回结果",
                )

            # 写入缓存
            await self._cache.set(cache_key, best_response)
            return best_response
        finally:
            if lock_acquired:
                await self._cache.release_lock(cache_key)

    async def search_comprehensive_intel(
        self,
        stock_code: str,
        stock_name: str = "",
        max_searches: int = 3,
    ) -> Dict[str, SearchResponse]:
        """多维度情报搜索。"""
        name = stock_name or stock_code
        queries = {
            key: tpl.format(name=name)
            for key, tpl in list(_INTEL_QUERIES.items())[:max_searches]
        }
        results: Dict[str, SearchResponse] = {}
        for dim, query in queries.items():
            results[dim] = await self.search(query, max_results=3, days=7)
        return results

    @staticmethod
    def format_intel_report(
        intel_results: Dict[str, SearchResponse],
        stock_name: str = "",
    ) -> str:
        """格式化情报文本。"""
        dim_labels = {
            "latest_news": "最新新闻",
            "market_analysis": "市场分析",
            "risk_check": "风险预警",
            "announcements": "公司公告",
            "earnings": "财报业绩",
            "industry": "行业动态",
        }
        lines: List[str] = []
        header = f"{stock_name} 综合情报" if stock_name else "综合情报"
        lines.append(f"=== {header} ===")
        for dim, response in intel_results.items():
            label = dim_labels.get(dim, dim)
            context = response.to_context(max_results=3)
            if context:
                lines.append(f"\n【{label}】\n{context}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    @staticmethod
    def _should_prefer_chinese_news(stock_code: str) -> bool:
        """A股代码判断 → 优先中文结果。"""
        return bool(stock_code and re.match(r"^\d{6}$", stock_code))

    @staticmethod
    def _prioritize_news_language(
        response: SearchResponse,
        prefer_chinese: bool = True,
    ) -> Tuple[SearchResponse, int]:
        """中文结果重排到前面。"""
        if not prefer_chinese or not response.results:
            return response, 0

        chinese = []
        other = []
        for r in response.results:
            if _CJK_PATTERN.search(r.title) or _CJK_PATTERN.search(r.snippet):
                chinese.append(r)
            else:
                other.append(r)

        preferred_count = len(chinese)
        reordered = chinese + other
        return SearchResponse(
            query=response.query,
            results=reordered,
            provider=response.provider,
            success=response.success,
            error_message=response.error_message,
            search_time=response.search_time,
        ), preferred_count

    @staticmethod
    def _normalize_news_publish_date(date_str: Optional[str]) -> Optional[datetime]:
        """日期归一化（支持 15+ 种格式）。"""
        if not date_str:
            return None
        date_str = date_str.strip()

        # 先尝试相对时间
        rel = _parse_relative_news_date(date_str)
        if rel is not None:
            return rel

        for fmt in _DATE_FORMATS:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        # 带时区的 ISO 格式
        try:
            return datetime.fromisoformat(date_str)
        except (ValueError, TypeError):
            pass

        return None

    @staticmethod
    def _filter_news_response(
        response: SearchResponse,
        max_age_days: int,
    ) -> SearchResponse:
        """时效窗口过滤 — 丢弃超出 max_age_days 的结果。"""
        if not response.results:
            return response

        cutoff = datetime.now() - timedelta(days=max_age_days)
        filtered: List[SearchResult] = []
        for r in response.results:
            dt = SearchService._normalize_news_publish_date(r.published_date)
            if dt is None or dt >= cutoff:
                filtered.append(r)

        return SearchResponse(
            query=response.query,
            results=filtered,
            provider=response.provider,
            success=response.success,
            error_message=response.error_message,
            search_time=response.search_time,
        )

    @staticmethod
    def _provider_request_size(max_results: int) -> int:
        """过采样计算 — 请求更多结果以补偿过滤损失。"""
        return min(max_results * 2, 20)

    @staticmethod
    def _cache_key(
        query: str,
        max_results: int,
        days: int,
        lang_pref: bool = False,
    ) -> str:
        """缓存 key 生成（MD5 短 hash）。"""
        raw = f"{query}|{max_results}|{days}|{lang_pref}"
        return hashlib.md5(raw.encode()).hexdigest()[:12]


# ──────────────────────────────────────────────
# 相对时间解析
# ──────────────────────────────────────────────

def _parse_relative_news_date(text: str) -> Optional[datetime]:
    """解析相对时间（今天/3天前/2 hours ago 等）。"""
    now = datetime.now()
    text = text.strip().lower()

    # 中文相对时间
    m = _RELATIVE_CN.search(text)
    if m:
        days_ago = m.group(1)
        hours_ago = m.group(2)
        minutes_ago = m.group(3)
        cn_word = m.group(4)
        if days_ago:
            return now - timedelta(days=int(days_ago))
        if hours_ago:
            return now - timedelta(hours=int(hours_ago))
        if minutes_ago:
            return now - timedelta(minutes=int(minutes_ago))
        if cn_word == "今天":
            return now
        if cn_word == "昨天":
            return now - timedelta(days=1)
        if cn_word == "前天":
            return now - timedelta(days=2)

    # 英文相对时间
    m = _RELATIVE_EN.search(text)
    if m:
        days_ago = m.group(1)
        hours_ago = m.group(2)
        minutes_ago = m.group(3)
        en_word = m.group(4)
        if days_ago:
            return now - timedelta(days=int(days_ago))
        if hours_ago:
            return now - timedelta(hours=int(hours_ago))
        if minutes_ago:
            return now - timedelta(minutes=int(minutes_ago))
        if en_word == "today":
            return now
        if en_word == "yesterday":
            return now - timedelta(days=1)

    return None
