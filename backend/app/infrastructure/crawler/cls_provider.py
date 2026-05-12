"""财联社信息源实现"""

import logging
import re
from datetime import datetime

import httpx

from app.infrastructure.crawler.base_provider import BaseEventProvider, CrawledArticle

logger = logging.getLogger(__name__)

# 财联社快讯 API（公开接口）
CLS_ROLL_URL = "https://www.cls.cn/api/sw?app=Cls2FinanceInfo&os=web&sv=8.4.6"


def _clean_html(text: str) -> str:
    """去除 HTML 标签"""
    return re.sub(r"<[^>]+>", "", text).strip()


class ClsProvider(BaseEventProvider):
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=15, follow_redirects=True)

    async def fetch_latest(self, limit: int = 50) -> list[CrawledArticle]:
        try:
            resp = await self.client.get(
                CLS_ROLL_URL,
                params={"rn": limit},
            )
            resp.raise_for_status()
            data = resp.json()
            articles = []
            for item in data.get("data", {}).get("roll_data", []):
                title = item.get("title", "").strip() or item.get("brief", "").strip()
                if not title:
                    continue
                content = _clean_html(item.get("content", "") or item.get("brief", ""))
                if len(content) > 500:
                    content = content[:500]
                published_at = None
                ctime = item.get("ctime")
                if ctime:
                    try:
                        published_at = datetime.fromtimestamp(int(ctime))
                    except (ValueError, TypeError):
                        pass
                articles.append(CrawledArticle(
                    title=title[:200],
                    url=item.get("url", ""),
                    content=content,
                    source="cls",
                    published_at=published_at,
                ))
            return articles[:limit]
        except Exception as e:
            logger.warning("财联社采集失败: %s", e)
            return []

    async def fetch_by_stock(self, stock_code: str, limit: int = 20) -> list[CrawledArticle]:
        # 财联社暂不支持按股票代码精确搜索，返回空
        return []

    async def fetch_by_keyword(self, keyword: str, limit: int = 20) -> list[CrawledArticle]:
        # 暂不支持关键词搜索
        return []
