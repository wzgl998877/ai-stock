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
        "done": "知识库检索完成",
    },
    "summarize_context": {
        "label": "整理信息",
        "running": "正在整理搜索和知识库信息...",
        "done": "信息整理完成",
    },
}

# 节点执行顺序（含条件节点）
NODE_ORDER = ["agent_classify", "web_search", "load", "retrieve", "summarize_context"]


def _route_after_classify(state: AnalysisState) -> str:
    """条件边：agent_classify 后根据 need_search 决定路径"""
    if state.get("need_search"):
        return "web_search"
    return "load"


def build_analysis_graph(session_factory=None, ai_service=None, search_service=None,
                         vector_search_repo=None, embedding_service=None):
    """
    构建分析预处理工作流:
        agent_classify → (条件) → web_search → load → retrieve → summarize_context → END
                                 → load → retrieve → summarize_context → END

    Args:
        session_factory: 异步上下文管理器，用于 retrieve 节点获取 DB session。
                         不传则跳过 retrieve 节点。
        ai_service: AIService 实例，用于 agent_classify 节点和 summarize_context 节点的 LLM 调用。
                    不传则降级使用规则判断的 classify_node。
        search_service: 统一搜索服务实例（可选），用于 web_search 节点。
        vector_search_repo: 向量检索仓储（可选），用于 retrieve 节点的语义检索。
        embedding_service: Embedding 服务（可选），用于 retrieve 节点的 query embedding。
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
        from app.infrastructure.workflow.nodes.web_search_node import create_web_search_node
        graph.add_node("web_search", create_web_search_node(search_service))

    # retrieve 节点
    has_retrieve = False
    if session_factory:
        from app.infrastructure.workflow.nodes.retrieve import create_retrieve_node
        graph.add_node("retrieve", create_retrieve_node(session_factory, vector_search_repo, embedding_service, ai_service))
        has_retrieve = True

    # summarize_context 节点（需要 ai_service 做总结）
    has_summarize = False
    if ai_service:
        from app.infrastructure.workflow.nodes.summarize_context import create_summarize_context_node
        graph.add_node("summarize_context", create_summarize_context_node(ai_service))
        has_summarize = True

    # === 边 ===
    graph.set_entry_point("agent_classify")

    if use_agent:
        # agent 模式：条件边
        graph.add_conditional_edges("agent_classify", _route_after_classify)
        graph.add_edge("web_search", "load")
    else:
        # 降级模式：线性
        graph.add_edge("agent_classify", "load")

    # load → retrieve → summarize_context → END
    if has_retrieve and has_summarize:
        graph.add_edge("load", "retrieve")
        graph.add_edge("retrieve", "summarize_context")
        graph.add_edge("summarize_context", END)
    elif has_summarize:
        # 无 retrieve，load 直接到 summarize
        graph.add_edge("load", "summarize_context")
        graph.add_edge("summarize_context", END)
    elif has_retrieve:
        graph.add_edge("load", "retrieve")
        graph.add_edge("retrieve", END)
    else:
        graph.add_edge("load", END)

    compiled = graph.compile()
    logger.info(
        "分析工作流 Graph 编译完成 (agent=%s, retrieve=%s, summarize=%s)",
        use_agent, has_retrieve, has_summarize,
    )
    return compiled
