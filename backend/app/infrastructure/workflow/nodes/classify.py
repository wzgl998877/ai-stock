"""classify 节点 — 判断输入类型（url / file / text）"""

import re
import logging

from app.infrastructure.workflow.state.analysis_state import AnalysisState

logger = logging.getLogger(__name__)

URL_PATTERN = re.compile(r"^https?://\S+$", re.IGNORECASE)

FILE_EXTENSIONS = {".pdf", ".doc", ".docx", ".txt", ".csv", ".xlsx"}


def classify_node(state: AnalysisState) -> dict:
    """
    判断用户输入类型。

    规则：
    1. 以 http:// 或 https:// 开头 → url
    2. 以已知文件扩展名结尾 → file
    3. 其他 → text
    """
    source = state.get("source", "").strip()

    if URL_PATTERN.match(source):
        input_type = "url"
    elif any(source.lower().endswith(ext) for ext in FILE_EXTENSIONS):
        input_type = "file"
    else:
        input_type = "text"

    logger.info("[classify] input_type=%s, source前50字=%s", input_type, source[:50])
    return {"input_type": input_type}
