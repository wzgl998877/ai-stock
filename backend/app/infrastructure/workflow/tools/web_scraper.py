"""URL 内容爬取工具"""

import logging
import warnings

import httpx
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

logger = logging.getLogger(__name__)

MAX_CONTENT_LENGTH = 10000
REQUEST_TIMEOUT = 30


async def scrape_url(url: str) -> str:
    """
    爬取 URL 页面正文文本。

    1. GET 请求获取 HTML
    2. BeautifulSoup 提取 <body> 内文本
    3. 清理多余空白，截断到 MAX_CONTENT_LENGTH
    """
    logger.info("[web_scraper] 开始爬取: %s", url)

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT, follow_redirects=True) as client:
        response = await client.get(url, headers={"User-Agent": "Mozilla/5.0 (compatible; AIStockBot/1.0)"})
        if response.status_code != 200:
            raise RuntimeError(f"HTTP {response.status_code}: 请求失败")

    soup = BeautifulSoup(response.text, "html.parser")

    # 移除无关标签
    for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
        tag.decompose()

    text = soup.get_text(separator="\n", strip=True)

    # 清理多余空行
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    text = "\n".join(lines)

    if len(text) > MAX_CONTENT_LENGTH:
        text = text[:MAX_CONTENT_LENGTH] + "...(内容已截断)"
        logger.info("[web_scraper] 内容已截断至 %d 字", MAX_CONTENT_LENGTH)

    if not text:
        raise RuntimeError("页面内容为空")

    logger.info("[web_scraper] 爬取完成, 长度=%d", len(text))
    return text
