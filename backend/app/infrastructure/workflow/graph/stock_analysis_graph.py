"""StockAnalysisGraph — 个股多Agent分析的 LangGraph 工作流编排"""

import logging
from typing import Optional

from langgraph.graph import StateGraph, END, START

from app.core.config import settings
from app.infrastructure.workflow.state.stock_analysis_state import (
    StockAnalysisInput,
    StockAnalysisWorking,
    StockAnalysisOutput,
)
from app.infrastructure.workflow.nodes.stock_market_analyst import create_market_analyst_node
from app.infrastructure.workflow.nodes.stock_fundamentals_analyst import create_fundamentals_analyst_node
from app.infrastructure.workflow.nodes.stock_news_analyst import create_news_analyst_node
from app.infrastructure.workflow.nodes.stock_sentiment_analyst import create_sentiment_analyst_node
from app.infrastructure.workflow.nodes.msg_clear import create_msg_clear_node
from app.infrastructure.workflow.nodes.bull_researcher import create_bull_researcher_node
from app.infrastructure.workflow.nodes.bear_researcher import create_bear_researcher_node
from app.infrastructure.workflow.nodes.research_manager import create_research_manager_node
from app.infrastructure.workflow.nodes.trader import create_trader_node
from app.infrastructure.workflow.nodes.risky_debator import create_risky_debator_node
from app.infrastructure.workflow.nodes.safe_debator import create_safe_debator_node
from app.infrastructure.workflow.nodes.neutral_debator import create_neutral_debator_node
from app.infrastructure.workflow.nodes.risk_judge import create_risk_judge_node
from app.infrastructure.workflow.nodes.signal_extractor_node import create_signal_extractor_node
from app.infrastructure.workflow.nodes.quick_decision_node import create_quick_decision_node

logger = logging.getLogger(__name__)

# 合并状态类（LangGraph 需要单一 State 类）
class StockAnalysisState(StockAnalysisInput, StockAnalysisWorking, StockAnalysisOutput, total=False):
    """个股分析工作流完整状态（合并 Input/Working/Output 三层）"""
    pass


# === 条件路由函数 ===

def _route_after_analysts(state: dict) -> str:
    """分析师阶段完成后，根据 analysis_mode 决定后续路径

    quick 模式 → quick_decision → END
    full 模式 → bull_researcher → 辩论流程
    """
    analysis_mode = state.get("analysis_mode", "full")
    if analysis_mode == "quick":
        return "quick_decision"
    return "bull_researcher"


def _should_continue_investment_debate(state: dict) -> str:
    """判断投资辩论是否继续

    看多 → 看空 → 看多 → ... 循环
    达到最大辩论轮次后 → research_manager
    """
    debate_state = state.get("investment_debate_state", {})
    round_count = debate_state.get("round", 0)
    max_rounds = settings.debate_rounds * 2  # 每轮包含bull+bear各一次

    if round_count >= max_rounds:
        return "research_manager"

    # 奇数轮（bull刚说完）→ bear，偶数轮（bear刚说完）→ bull
    current_agent = state.get("current_agent", "")
    if current_agent == "bull_researcher":
        return "bear_researcher"
    else:
        return "bull_researcher"


def _should_continue_risk_debate(state: dict) -> str:
    """判断风险辩论是否继续

    risky → safe → neutral → risky → ... 循环
    达到最大轮次后 → risk_judge
    """
    risk_state = state.get("risk_debate_state", {})
    round_count = risk_state.get("round", 0)
    max_rounds = settings.risk_debate_rounds * 3  # 每轮包含risky+safe+neutral各一次

    if round_count >= max_rounds:
        return "risk_judge"

    # 根据当前 agent 决定下一个
    current_agent = state.get("current_agent", "")
    if current_agent == "risky_debator":
        return "safe_debator"
    elif current_agent == "safe_debator":
        return "neutral_debator"
    else:
        return "risky_debator"


def build_stock_analysis_graph(ai_service, config: Optional[dict] = None) -> StateGraph:
    """
    构建个股多Agent分析工作流图。

    图结构：
        START → market_analyst → fundamentals_analyst → news_analyst → sentiment_analyst
        → 条件路由
            quick模式 → quick_decision → END
            full模式 → bull_researcher ⇄ bear_researcher (辩论循环)
            → research_manager → trader → risky_debator ⇄ safe_debator ⇄ neutral_debator (风险辩论循环)
            → risk_judge → signal_extractor → END

    Args:
        ai_service: AIService 实例
        config: 可选配置字典，可覆盖默认参数

    Returns:
        编译后的 LangGraph 图
    """
    max_tool_calls = (config or {}).get("max_tool_calls", settings.max_tool_calls)

    graph = StateGraph(StockAnalysisState)

    # === 添加节点 ===

    # 分析师节点
    graph.add_node("market_analyst", create_market_analyst_node(ai_service, max_tool_calls=max_tool_calls))
    graph.add_node("fundamentals_analyst", create_fundamentals_analyst_node(ai_service, max_tool_calls=max_tool_calls))
    graph.add_node("news_analyst", create_news_analyst_node(ai_service, max_tool_calls=max_tool_calls))
    graph.add_node("sentiment_analyst", create_sentiment_analyst_node(ai_service, max_tool_calls=max_tool_calls))

    # 消息清除节点（每个分析师后清理工具调用消息）
    graph.add_node("msg_clear_market", create_msg_clear_node("market_analyst"))
    graph.add_node("msg_clear_fundamentals", create_msg_clear_node("fundamentals_analyst"))
    graph.add_node("msg_clear_news", create_msg_clear_node("news_analyst"))
    graph.add_node("msg_clear_sentiment", create_msg_clear_node("sentiment_analyst"))

    # 辩论节点
    graph.add_node("bull_researcher", create_bull_researcher_node(ai_service))
    graph.add_node("bear_researcher", create_bear_researcher_node(ai_service))

    # 研究管理器
    graph.add_node("research_manager", create_research_manager_node(ai_service))

    # 交易员
    graph.add_node("trader", create_trader_node(ai_service))

    # 风险辩论节点
    graph.add_node("risky_debator", create_risky_debator_node(ai_service))
    graph.add_node("safe_debator", create_safe_debator_node(ai_service))
    graph.add_node("neutral_debator", create_neutral_debator_node(ai_service))

    # 风险裁决
    graph.add_node("risk_judge", create_risk_judge_node(ai_service))

    # 信号提取
    graph.add_node("signal_extractor", create_signal_extractor_node(ai_service))

    # 快速决策
    graph.add_node("quick_decision", create_quick_decision_node(ai_service))

    # === 添加边 ===

    # START → 第一个分析师
    graph.add_edge(START, "market_analyst")

    # 分析师链：market → msg_clear → fundamentals → msg_clear → news → msg_clear → sentiment → msg_clear
    graph.add_edge("market_analyst", "msg_clear_market")
    graph.add_edge("msg_clear_market", "fundamentals_analyst")
    graph.add_edge("fundamentals_analyst", "msg_clear_fundamentals")
    graph.add_edge("msg_clear_fundamentals", "news_analyst")
    graph.add_edge("news_analyst", "msg_clear_news")
    graph.add_edge("msg_clear_news", "sentiment_analyst")
    graph.add_edge("sentiment_analyst", "msg_clear_sentiment")

    # 分析师完成后：条件路由（quick / full）
    graph.add_conditional_edges(
        "msg_clear_sentiment",
        _route_after_analysts,
        {
            "quick_decision": "quick_decision",
            "bull_researcher": "bull_researcher",
        },
    )

    # quick 模式 → END
    graph.add_edge("quick_decision", END)

    # 投资辩论循环：bull ⇄ bear，达到最大轮次 → research_manager
    graph.add_conditional_edges(
        "bull_researcher",
        _should_continue_investment_debate,
        {
            "bear_researcher": "bear_researcher",
            "research_manager": "research_manager",
        },
    )
    graph.add_conditional_edges(
        "bear_researcher",
        _should_continue_investment_debate,
        {
            "bull_researcher": "bull_researcher",
            "research_manager": "research_manager",
        },
    )

    # research_manager → trader
    graph.add_edge("research_manager", "trader")

    # trader → risky_debator（开始风险辩论）
    graph.add_edge("trader", "risky_debator")

    # 风险辩论循环：risky ⇄ safe ⇄ neutral，达到最大轮次 → risk_judge
    graph.add_conditional_edges(
        "risky_debator",
        _should_continue_risk_debate,
        {
            "safe_debator": "safe_debator",
            "risk_judge": "risk_judge",
        },
    )
    graph.add_conditional_edges(
        "safe_debator",
        _should_continue_risk_debate,
        {
            "neutral_debator": "neutral_debator",
            "risk_judge": "risk_judge",
        },
    )
    graph.add_conditional_edges(
        "neutral_debator",
        _should_continue_risk_debate,
        {
            "risky_debator": "risky_debator",
            "risk_judge": "risk_judge",
        },
    )

    # risk_judge → signal_extractor → END
    graph.add_edge("risk_judge", "signal_extractor")
    graph.add_edge("signal_extractor", END)

    # === 编译图 ===
    compiled = graph.compile()
    logger.info("个股分析工作流 Graph 编译完成")
    return compiled
