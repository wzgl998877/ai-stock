"""财联社信息源实现"""

import logging
import re
from datetime import datetime

import httpx

from app.infrastructure.crawler.base_provider import BaseEventProvider, CrawledArticle

logger = logging.getLogger(__name__)

# 财联社新版电报 API（旧 /nodeapi/updateTelegraphList 已下线）
# 必需参数：app（标识来源）、name（数据源）、lastTime（时间戳，0=拉最新）、rn（条数）
# sign/sv/os 参数经测试无需传递，服务端不校验
CLS_API_URL = "https://www.cls.cn/api/cache"

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.cls.cn/telegraph",
    "Accept": "application/json, text/plain, */*",
}


def _clean_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text).strip()


class ClsProvider(BaseEventProvider):
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=15, follow_redirects=True, headers=_HEADERS)

    async def fetch_latest(self, limit: int = 50) -> list[CrawledArticle]:
        try:
            resp = await self.client.get(
                CLS_API_URL,
                params={"app": "CailianpressWeb", "name": "telegraphList", "lastTime": 0, "rn": limit},
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("errno") != 0:
                logger.warning("财联社 API 返回异常 errno=%s", data.get("errno"))
                return []

            articles = []
            for item in data.get("data", {}).get("roll_data", []):
                title = item.get("title", "").strip() or item.get("brief", "").strip()
                if not title:
                    # 无标题无内容的条目跳过
                    content_raw = item.get("content", "") or item.get("brief", "")
                    if not content_raw.strip():
                        continue
                    # 截取前 30 字作为标题
                    title = content_raw[:30].strip()
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
                    url=f"https://www.cls.cn/detail/{item.get('id', '')}",
                    content=content,
                    source="cls",
                    published_at=published_at,
                ))
            return articles[:limit]
        except Exception as e:
            logger.warning("财联社采集失败: %s", e)
            return []

    async def fetch_by_stock(self, stock_code: str, limit: int = 20) -> list[CrawledArticle]:
        return []

    async def fetch_by_keyword(self, keyword: str, limit: int = 20) -> list[CrawledArticle]:
        return []
