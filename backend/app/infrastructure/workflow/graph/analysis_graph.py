"""分析预处理工作流 Graph 定义"""

import logging

from langgraph.graph import StateGraph, END

from app.infrastructure.workflow.state.analysis_state import AnalysisState
from app.infrastructure.workflow.nodes.classify import classify_node
from app.infrastructure.workflow.nodes.load import load_node

logger = logging.getLogger(__name__)

# 思维链步骤元数据：用于 ChatUseCase yield thinking SSE 事件
THINKING_STEP_META = {
    "classify": {
        "label": "判断输入类型",
        "running": "正在判断输入类型...",
        "done": "判断输入类型完成",
    },
    "load": {
        "label": "加载内容",
        "running": "正在加载内容...",
        "done": "内容加载完成",
    },
    "retrieve": {
        "label": "搜索知识库",
        "running": "正在搜索知识库...",
        "done": "搜索知识库完成",
    },
}

# 节点执行顺序
NODE_ORDER = ["classify", "load", "retrieve"]


def build_analysis_graph(session_factory=None):
    """
    构建分析预处理工作流: classify -> load -> retrieve -> END

    Args:
        session_factory: 异步上下文管理器，用于 retrieve 节点获取 DB session。
                         不传则跳过 retrieve 节点。
    """
    graph = StateGraph(AnalysisState)

    # 添加节点
    graph.add_node("classify", classify_node)
    graph.add_node("load", load_node)

    if session_factory:
        from app.infrastructure.workflow.nodes.retrieve import create_retrieve_node
        graph.add_node("retrieve", create_retrieve_node(session_factory))

    # 设置入口和边
    graph.set_entry_point("classify")
    graph.add_edge("classify", "load")

    if session_factory:
        graph.add_edge("load", "retrieve")
        graph.add_edge("retrieve", END)
    else:
        graph.add_edge("load", END)

    compiled = graph.compile()
    logger.info("分析工作流 Graph 编译完成 (retrieve=%s)", "enabled" if session_factory else "disabled")
    return compiled
