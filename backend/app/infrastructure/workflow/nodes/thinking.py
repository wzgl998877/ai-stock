"""thinking 辅助模块 — 供各节点生成思维链描述信息"""

from app.infrastructure.workflow.state.analysis_state import AnalysisState


def make_thinking_done_msg(node_name: str, state_update: dict) -> str:
    """
    根据节点名称和状态更新，生成「完成」阶段的描述消息。
    节点可以将 thinking_done_msg 写入 state，供 ChatUseCase 直接使用。
    """
    if node_name == "classify":
        input_type = state_update.get("input_type", "text")
        type_labels = {"url": "网页链接", "file": "文件", "text": "文本"}
        return f"判断输入类型: {type_labels.get(input_type, input_type)}"

    if node_name == "load":
        raw_text = state_update.get("raw_text", "")
        error = state_update.get("error")
        if error:
            return f"内容加载完成（降级）"
        length = len(raw_text) if raw_text else 0
        return f"内容加载完成，共 {length} 字"

    if node_name == "retrieve":
        results = state_update.get("search_results", [])
        count = len(results)
        if count == 0:
            return "知识库检索完成，未找到相关文章"
        return f"知识库检索完成，找到 {count} 篇相关文章"

    return f"{node_name} 完成"


def make_thinking_running_msg(node_name: str, state: AnalysisState) -> str:
    """
    根据节点名称和当前状态，生成「运行中」阶段的描述消息。
    """
    if node_name == "classify":
        return "正在判断输入类型..."

    if node_name == "load":
        input_type = state.get("input_type", "text")
        if input_type == "url":
            return "正在抓取网页内容..."
        if input_type == "file":
            return "正在解析文件..."
        return "正在加载内容..."

    if node_name == "retrieve":
        return "正在搜索知识库..."

    return f"正在{node_name}..."
