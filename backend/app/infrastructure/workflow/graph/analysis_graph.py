"""分析预处理工作流 Graph 定义"""

import logging

from langgraph.graph import StateGraph, END

from app.infrastructure.workflow.state.analysis_state import AnalysisState
from app.infrastructure.workflow.nodes.load import load_node

logger = logging.getLogger(__name__)

# 思维链步骤元数据：用于 ChatUseCase yield thinking SSE 事件
THINKING_STEP_META = {
    "agent_classify": {
        "label": "判断输入类型",
        "running": "正在判断输入类型...",
        "done": "判断输入类型完成",
    },
    "web_search": {
        "label": "搜索互联网",
        "running": "正在搜索互联网...",
        "done": "搜索互联网完成",
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

# 节点执行顺序（含条件节点）
NODE_ORDER = ["agent_classify", "web_search", "load", "retrieve"]


def _route_after_classify(state: AnalysisState) -> str:
    """条件边：agent_classify 后根据 need_search 决定路径"""
    if state.get("need_search"):
        return "web_search"
    return "load"


def build_analysis_graph(session_factory=None, ai_service=None):
    """
    构建分析预处理工作流:
        agent_classify → (条件) → web_search → load → retrieve → END
                                 → load → retrieve → END

    Args:
        session_factory: 异步上下文管理器，用于 retrieve 节点获取 DB session。
                         不传则跳过 retrieve 节点。
        ai_service: AIService 实例，用于 agent_classify 节点的 LLM 调用。
                    不传则降级使用规则判断的 classify_node。
    """
    graph = StateGraph(AnalysisState)

    # 选择 classify 节点
    if ai_service:
        from app.infrastructure.workflow.nodes.agent_classify import create_agent_classify_node
        graph.add_node("agent_classify", create_agent_classify_node(ai_service))
        use_agent = True
    else:
        from app.infrastructure.workflow.nodes.classify import classify_node
        graph.add_node("agent_classify", classify_node)
        use_agent = False

    graph.add_node("load", load_node)

    # web_search 节点（仅 agent 模式）
    if use_agent:
        from app.infrastructure.workflow.nodes.web_search_node import web_search_node
        graph.add_node("web_search", web_search_node)

    # retrieve 节点
    has_retrieve = False
    if session_factory:
        from app.infrastructure.workflow.nodes.retrieve import create_retrieve_node
        graph.add_node("retrieve", create_retrieve_node(session_factory))
        has_retrieve = True

    # === 边 ===
    graph.set_entry_point("agent_classify")

    if use_agent:
        # agent 模式：条件边
        graph.add_conditional_edges("agent_classify", _route_after_classify)
        graph.add_edge("web_search", "load")
    else:
        # 降级模式：线性
        graph.add_edge("agent_classify", "load")

    if has_retrieve:
        graph.add_edge("load", "retrieve")
        graph.add_edge("retrieve", END)
    else:
        graph.add_edge("load", END)

    compiled = graph.compile()
    logger.info(
        "分析工作流 Graph 编译完成 (agent=%s, retrieve=%s)",
        use_agent, has_retrieve,
    )
    return compiled
