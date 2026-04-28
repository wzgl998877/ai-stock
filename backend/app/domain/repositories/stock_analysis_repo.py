"""StockAnalysisRepository — 个股分析仓储接口"""

from abc import ABC, abstractmethod
from typing import Optional, List, Tuple

from app.domain.entities.stock_analysis import StockAnalysis, StockAnalysisDetail


class StockAnalysisRepository(ABC):
    """个股分析仓储接口"""

    @abstractmethod
    async def create(self, analysis: StockAnalysis) -> StockAnalysis:
        """创建分析主记录 + 预创建所有 agent detail 记录（status=pending）"""
        ...

    @abstractmethod
    async def get_by_id(self, analysis_id: str) -> Optional[StockAnalysis]:
        """获取分析记录（含 details）"""
        ...

    @abstractmethod
    async def get_by_article_id(self, article_id: str) -> Optional[StockAnalysis]:
        """通过 article_id 查找分析记录"""
        ...

    @abstractmethod
    async def list_by_user(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
    ) -> Tuple[List[StockAnalysis], int]:
        """用户分析记录列表（分页）"""
        ...

    @abstractmethod
    async def list_by_stock(
        self,
        stock_code: str,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[StockAnalysis], int]:
        """按股票代码查询分析记录"""
        ...

    @abstractmethod
    async def get_recent_by_stock(self, stock_code: str, user_id: str, minutes: int = 5) -> Optional[StockAnalysis]:
        """查询某股票最近的分析记录"""
        ...

    @abstractmethod
    async def get_in_progress_by_user(self, user_id: str) -> Optional[StockAnalysis]:
        """查询用户正在进行的分析记录"""
        ...

    @abstractmethod
    async def update_status(self, analysis_id: str, status: str, current_phase: Optional[str] = None) -> None:
        """更新分析状态和当前阶段"""
        ...

    @abstractmethod
    async def update_result(
        self,
        analysis_id: str,
        title: str,
        summary: str,
        full_content: str,
        decision_action: Optional[str] = None,
        target_price: Optional[float] = None,
        stop_loss_price: Optional[float] = None,
        confidence: Optional[float] = None,
        risk_score: Optional[float] = None,
        reasoning: Optional[str] = None,
        industries: Optional[List[str]] = None,
    ) -> None:
        """更新分析结果"""
        ...

    @abstractmethod
    async def update_detail_by_agent(
        self,
        analysis_id: str,
        agent_name: str,
        status: Optional[str] = None,
        summary: Optional[str] = None,
        full_report: Optional[str] = None,
        thinking_steps: Optional[list] = None,
        debate_data: Optional[dict] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """按 agent_name 更新分析详情"""
        ...

    @abstractmethod
    async def sync_to_article(self, analysis_id: str) -> Optional[str]:
        """将分析结果同步到 t_analysis_article 知识库，返回 article_id"""
        ...
