"""load 节点 — 根据输入类型加载内容为纯文本"""

import logging

from app.infrastructure.workflow.state.analysis_state import AnalysisState

logger = logging.getLogger(__name__)


async def load_node(state: AnalysisState) -> dict:
    """
    根据输入类型加载内容：
    - text: 直接透传
    - url:  调用 web_scraper 爬取
    - file: 预留，MVP 返回提示文本
    """
    input_type = state.get("input_type", "text")
    source = state.get("source", "")

    if input_type == "text":
        raw_text = source

    elif input_type == "url":
        from app.infrastructure.workflow.tools.web_scraper import scrape_url
        try:
            raw_text = await scrape_url(source)
        except Exception as e:
            logger.error("[load] URL爬取失败: %s, error=%s", source, e)
            return {"raw_text": source, "error": f"URL内容获取失败: {str(e)}"}

    elif input_type == "file":
        raw_text = f"[文件内容解析暂未支持] 原始输入: {source}"
        logger.warning("[load] 文件类型暂不支持: %s", source)

    else:
        raw_text = source

    logger.info("[load] input_type=%s, raw_text长度=%d", input_type, len(raw_text))
    return {"raw_text": raw_text}
