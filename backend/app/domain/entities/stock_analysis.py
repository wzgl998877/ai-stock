"""StockAnalysis + StockAnalysisDetail 领域实体"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any


@dataclass
class StockAnalysisDetail:
    """分析详情 — 每个 Agent 一条记录"""
    detail_id: str
    analysis_id: str
    agent_name: str
    phase: str  # analysts / debate / trader / risk
    status: str = "pending"  # pending / running / done / failed
    summary: Optional[str] = None
    full_report: Optional[str] = None
    thinking_steps: Optional[List[Dict[str, Any]]] = None
    debate_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    completed_at: Optional[datetime] = None
    display_order: int = 0
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None


@dataclass
class StockAnalysis:
    """个股分析主记录"""
    analysis_id: str
    stock_code: str
    stock_name: str
    user_id: str
    analysis_mode: str = "full"  # quick / full
    status: str = "pending"  # pending / in_progress / completed / stopped / failed
    current_phase: str = "analysts"  # analysts / debate / trader / risk / done
    title: str = ""
    summary: str = ""
    full_content: Optional[str] = None
    decision_action: Optional[str] = None
    target_price: Optional[Decimal] = None
    stop_loss_price: Optional[Decimal] = None
    confidence: Optional[Decimal] = None
    risk_score: Optional[Decimal] = None
    reasoning: Optional[str] = None
    industries: Optional[List[str]] = None
    data_source: str = ""
    article_id: Optional[str] = None
    session_id: Optional[str] = None
    # 关联详情
    details: List[StockAnalysisDetail] = field(default_factory=list)
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None
