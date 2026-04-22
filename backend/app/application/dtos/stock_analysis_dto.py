"""个股分析 DTO — 请求/响应数据传输对象"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class StockAnalysisConfigDTO:
    """个股分析配置"""
    stock_code: str = ""
    stock_name: str = ""
    analysis_mode: str = "full"  # quick | full
    debate_rounds: int = 2
    risk_debate_rounds: int = 2


@dataclass
class StockValidationDTO:
    """股票代码验证结果"""
    valid: bool = False
    stock_code: str = ""
    stock_name: str = ""
    market: str = ""  # sh | sz
    message: str = ""


@dataclass
class RecentAnalysisDTO:
    """近期分析检查结果"""
    has_recent: bool = False
    article_id: str = ""
    title: str = ""
    created_at: str = ""


@dataclass
class AgentStatusDTO:
    """Agent状态事件"""
    agent: str = ""
    phase: str = ""
    status: str = ""  # running | done | failed


@dataclass
class DebateDTO:
    """辩论事件"""
    speaker: str = ""  # bull | bear | risky | safe | neutral
    round: int = 1
    content: str = ""


@dataclass
class DecisionDTO:
    """结构化决策"""
    action: str = ""  # 买入 | 持有 | 卖出
    target_price: float = 0.0
    confidence: float = 0.0  # 0-1
    risk_score: float = 0.0  # 0-1
    reasoning: str = ""
