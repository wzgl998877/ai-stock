"""StockAnalysisState — 个股多Agent分析的三层状态定义"""

from typing import Optional, TypedDict


class StockAnalysisInput(TypedDict, total=False):
    """输入层：发起分析时的参数"""
    stock_code: str
    stock_name: str
    analysis_mode: str  # "quick" | "full"


class StockAnalysisWorking(TypedDict, total=False):
    """工作层：分析过程中的中间状态"""
    # 分析师阶段
    market_report: str
    fundamentals_report: str
    news_report: str
    sentiment_report: str
    # 工具调用计数（防死循环）
    market_tool_call_count: int
    fundamentals_tool_call_count: int
    news_tool_call_count: int
    sentiment_tool_call_count: int
    # 辩论阶段
    investment_debate_state: dict
    investment_plan: str
    trader_investment_plan: str
    # 风险辩论阶段
    risk_debate_state: dict
    # 进度追踪
    current_agent: str
    current_phase: str  # "analysts" | "debate" | "trader" | "risk" | "done"
    # 消息列表（Agent间传递）
    messages: list[dict]


class StockAnalysisOutput(TypedDict, total=False):
    """输出层：分析完成后的结果"""
    title: str
    summary: str
    industries: list[str]
    final_decision: str
    action: str  # 买入/持有/卖出
    target_price: float
    confidence: float  # 0-1
    risk_score: float  # 0-1
    reasoning: str
    error: Optional[str]
