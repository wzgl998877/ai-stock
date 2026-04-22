"""AgentType 值对象 — 多Agent分析中的Agent标识枚举"""

from enum import Enum


class AgentType(str, Enum):
    """Agent标识枚举，对应多Agent分析流程中的各角色"""
    # 分析师阶段
    MARKET_ANALYST = "market_analyst"
    FUNDAMENTALS_ANALYST = "fundamentals_analyst"
    NEWS_ANALYST = "news_analyst"
    SENTIMENT_ANALYST = "sentiment_analyst"
    # 辩论阶段
    BULL_RESEARCHER = "bull_researcher"
    BEAR_RESEARCHER = "bear_researcher"
    RESEARCH_MANAGER = "research_manager"
    # 交易阶段
    TRADER = "trader"
    # 风险辩论阶段
    RISKY_DEBATOR = "risky_debator"
    SAFE_DEBATOR = "safe_debator"
    NEUTRAL_DEBATOR = "neutral_debator"
    RISK_JUDGE = "risk_judge"


# Agent中文显示名映射
AGENT_DISPLAY_NAMES: dict[str, str] = {
    AgentType.MARKET_ANALYST: "技术面分析",
    AgentType.FUNDAMENTALS_ANALYST: "基本面分析",
    AgentType.NEWS_ANALYST: "新闻分析",
    AgentType.SENTIMENT_ANALYST: "情绪分析",
    AgentType.BULL_RESEARCHER: "看多论证",
    AgentType.BEAR_RESEARCHER: "看空论证",
    AgentType.RESEARCH_MANAGER: "研究管理器",
    AgentType.TRADER: "交易决策",
    AgentType.RISKY_DEBATOR: "激进风险观点",
    AgentType.SAFE_DEBATOR: "保守风险观点",
    AgentType.NEUTRAL_DEBATOR: "中立风险观点",
    AgentType.RISK_JUDGE: "风险裁决",
}

# Agent所属阶段映射
AGENT_PHASE_MAPPING: dict[str, str] = {
    AgentType.MARKET_ANALYST: "analysts",
    AgentType.FUNDAMENTALS_ANALYST: "analysts",
    AgentType.NEWS_ANALYST: "analysts",
    AgentType.SENTIMENT_ANALYST: "analysts",
    AgentType.BULL_RESEARCHER: "debate",
    AgentType.BEAR_RESEARCHER: "debate",
    AgentType.RESEARCH_MANAGER: "debate",
    AgentType.TRADER: "trader",
    AgentType.RISKY_DEBATOR: "risk",
    AgentType.SAFE_DEBATOR: "risk",
    AgentType.NEUTRAL_DEBATOR: "risk",
    AgentType.RISK_JUDGE: "risk",
}

# 分析阶段枚举
ANALYSIS_PHASES = ["analysts", "debate", "trader", "risk", "done"]
