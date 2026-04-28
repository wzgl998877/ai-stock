"""MySQL StockAnalysis Repository — 操作 t_stock_analysis + t_stock_analysis_detail"""

import uuid
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, List, Tuple

from sqlalchemy import select, func, and_, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.stock_analysis import StockAnalysis, StockAnalysisDetail
from app.domain.repositories.stock_analysis_repo import StockAnalysisRepository
from app.infrastructure.db.models import (
    StockAnalysisModel,
    StockAnalysisDetailModel,
    AnalysisArticle,
    ArticleStock,
)

logger = logging.getLogger(__name__)

# full 模式所有 agent
FULL_MODE_AGENTS = [
    ("market_analyst", "analysts", 0),
    ("fundamentals_analyst", "analysts", 1),
    ("news_analyst", "analysts", 2),
    ("sentiment_analyst", "analysts", 3),
    ("bull_researcher", "debate", 4),
    ("bear_researcher", "debate", 5),
    ("research_manager", "debate", 6),
    ("trader", "trader", 7),
    ("risky_debator", "risk", 8),
    ("safe_debator", "risk", 9),
    ("neutral_debator", "risk", 10),
    ("risk_judge", "risk", 11),
]

# quick 模式只有 2 个 agent
QUICK_MODE_AGENTS = [
    ("market_analyst", "analysts", 0),
    ("fundamentals_analyst", "analysts", 1),
    ("trader", "trader", 2),
]


def _detail_to_entity(model: StockAnalysisDetailModel) -> StockAnalysisDetail:
    return StockAnalysisDetail(
        detail_id=model.detail_id,
        analysis_id=model.analysis_id,
        agent_name=model.agent_name,
        phase=model.phase,
        status=model.status,
        summary=model.summary,
        full_report=model.full_report,
        thinking_steps=model.thinking_steps,
        debate_data=model.debate_data,
        error_message=model.error_message,
        completed_at=model.completed_at,
        display_order=model.display_order,
        create_time=model.create_time,
        update_time=model.update_time,
    )


def _to_entity(model: StockAnalysisModel) -> StockAnalysis:
    return StockAnalysis(
        analysis_id=model.analysis_id,
        stock_code=model.stock_code,
        stock_name=model.stock_name,
        user_id=model.user_id,
        analysis_mode=model.analysis_mode,
        status=model.status,
        current_phase=model.current_phase,
        title=model.title,
        summary=model.summary,
        full_content=model.full_content,
        decision_action=model.decision_action,
        target_price=model.target_price,
        stop_loss_price=model.stop_loss_price,
        confidence=model.confidence,
        risk_score=model.risk_score,
        reasoning=model.reasoning,
        industries=model.industries,
        data_source=model.data_source,
        article_id=model.article_id,
        session_id=model.session_id,
        details=[_detail_to_entity(d) for d in model.details],
        create_time=model.create_time,
        update_time=model.update_time,
    )


class MySQLStockAnalysisRepository(StockAnalysisRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, analysis: StockAnalysis) -> StockAnalysis:
        """创建分析主记录 + 预创建所有 agent detail 记录"""
        # 确定要创建的 agent 列表
        agents = FULL_MODE_AGENTS if analysis.analysis_mode == "full" else QUICK_MODE_AGENTS

        model = StockAnalysisModel(
            analysis_id=analysis.analysis_id or uuid.uuid4().hex,
            stock_code=analysis.stock_code,
            stock_name=analysis.stock_name,
            user_id=analysis.user_id,
            analysis_mode=analysis.analysis_mode,
            status=analysis.status,
            current_phase=analysis.current_phase,
            session_id=analysis.session_id,
            data_source=analysis.data_source,
        )
        self.session.add(model)

        # 预创建所有 agent detail 记录
        for agent_name, phase, order in agents:
            detail = StockAnalysisDetailModel(
                detail_id=uuid.uuid4().hex,
                analysis_id=model.analysis_id,
                agent_name=agent_name,
                phase=phase,
                status="pending",
                display_order=order,
            )
            self.session.add(detail)

        await self.session.flush()
        analysis.analysis_id = model.analysis_id
        analysis.create_time = model.create_time
        return analysis

    async def get_by_id(self, analysis_id: str) -> Optional[StockAnalysis]:
        stmt = (
            select(StockAnalysisModel)
            .where(
                StockAnalysisModel.analysis_id == analysis_id,
                StockAnalysisModel.deleted == "0",
            )
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def get_by_article_id(self, article_id: str) -> Optional[StockAnalysis]:
        stmt = (
            select(StockAnalysisModel)
            .where(
                StockAnalysisModel.article_id == article_id,
                StockAnalysisModel.deleted == "0",
            )
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def list_by_user(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
    ) -> Tuple[List[StockAnalysis], int]:
        conditions = [
            StockAnalysisModel.user_id == user_id,
            StockAnalysisModel.deleted == "0",
        ]
        if status:
            conditions.append(StockAnalysisModel.status == status)

        where = and_(*conditions)

        count_stmt = select(func.count()).select_from(StockAnalysisModel).where(where)
        total = (await self.session.execute(count_stmt)).scalar() or 0

        stmt = (
            select(StockAnalysisModel)
            .where(where)
            .order_by(StockAnalysisModel.update_time.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()

        return [_to_entity(m) for m in models], total

    async def list_by_stock(
        self,
        stock_code: str,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[StockAnalysis], int]:
        conditions = [
            StockAnalysisModel.stock_code == stock_code,
            StockAnalysisModel.user_id == user_id,
            StockAnalysisModel.deleted == "0",
        ]
        where = and_(*conditions)

        count_stmt = select(func.count()).select_from(StockAnalysisModel).where(where)
        total = (await self.session.execute(count_stmt)).scalar() or 0

        stmt = (
            select(StockAnalysisModel)
            .where(where)
            .order_by(StockAnalysisModel.create_time.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()

        return [_to_entity(m) for m in models], total

    async def get_recent_by_stock(self, stock_code: str, user_id: str, minutes: int = 5) -> Optional[StockAnalysis]:
        cutoff = datetime.now() - timedelta(minutes=minutes)
        stmt = (
            select(StockAnalysisModel)
            .where(
                StockAnalysisModel.stock_code == stock_code,
                StockAnalysisModel.user_id == user_id,
                StockAnalysisModel.create_time >= cutoff,
                StockAnalysisModel.deleted == "0",
            )
            .order_by(StockAnalysisModel.create_time.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def get_in_progress_by_user(self, user_id: str) -> Optional[StockAnalysis]:
        stmt = (
            select(StockAnalysisModel)
            .where(
                StockAnalysisModel.user_id == user_id,
                StockAnalysisModel.status.in_(["pending", "in_progress"]),
                StockAnalysisModel.deleted == "0",
            )
            .order_by(StockAnalysisModel.create_time.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def update_status(self, analysis_id: str, status: str, current_phase: Optional[str] = None) -> None:
        stmt = select(StockAnalysisModel).where(StockAnalysisModel.analysis_id == analysis_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        if model:
            model.status = status
            if current_phase is not None:
                model.current_phase = current_phase
            await self.session.flush()
            await self.session.commit()

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
        stmt = select(StockAnalysisModel).where(StockAnalysisModel.analysis_id == analysis_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        if model:
            model.title = title
            model.summary = summary
            model.full_content = full_content
            model.status = "completed"
            model.current_phase = "done"
            if decision_action is not None:
                model.decision_action = decision_action
            if target_price is not None:
                model.target_price = Decimal(str(target_price))
            if stop_loss_price is not None:
                model.stop_loss_price = Decimal(str(stop_loss_price))
            if confidence is not None:
                # LLM 可能返回 0~100 的百分比值，数据库 DECIMAL(5,4) 只接受 0~1
                c = float(confidence)
                if c > 1:
                    c = c / 100
                model.confidence = Decimal(str(round(c, 4)))
            if risk_score is not None:
                r = float(risk_score)
                if r > 1:
                    r = r / 100
                model.risk_score = Decimal(str(round(r, 4)))
            if reasoning is not None:
                model.reasoning = reasoning
            if industries is not None:
                model.industries = industries
            await self.session.flush()
            await self.session.commit()

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
        """按 agent_name 更新分析详情，增量更新 + 立即 commit 使外部查询可见"""
        stmt = select(StockAnalysisDetailModel).where(
            StockAnalysisDetailModel.analysis_id == analysis_id,
            StockAnalysisDetailModel.agent_name == agent_name,
            StockAnalysisDetailModel.deleted == "0",
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        if model:
            if status is not None:
                model.status = status
            if summary is not None:
                model.summary = summary
            if full_report is not None:
                model.full_report = full_report
            if thinking_steps is not None:
                model.thinking_steps = thinking_steps
            if debate_data is not None:
                model.debate_data = debate_data
            if error_message is not None:
                model.error_message = error_message
            if status == "done":
                model.completed_at = datetime.now()
            await self.session.flush()
            await self.session.commit()

    async def sync_to_article(self, analysis_id: str) -> Optional[str]:
        """将分析结果同步到 t_analysis_article 知识库，返回 article_id"""
        analysis = await self.get_by_id(analysis_id)
        if not analysis:
            return None

        article_id = analysis.article_id or uuid.uuid4().hex

        # 构建 analysis_data JSON（兼容旧格式，便于前端回退查看）
        agents = {}
        for d in analysis.details:
            if d.status == "done" and d.summary:
                # agent_name 去掉 _analyst / _researcher 等后缀，取前缀作为 key
                key = d.agent_name.replace("_analyst", "").replace("_researcher", "").replace("_debator", "").replace("_judge", "")
                agents[key] = {
                    "status": "done",
                    "summary": d.summary,
                    "full_report": d.full_report or "",
                }

        analysis_data = {
            "stock_code": analysis.stock_code,
            "stock_name": analysis.stock_name,
            "analysis_mode": analysis.analysis_mode,
            "agents": agents,
            "decision": {
                "action": analysis.decision_action or "",
                "target_price": float(analysis.target_price) if analysis.target_price else 0.0,
                "stop_loss_price": float(analysis.stop_loss_price) if analysis.stop_loss_price else 0.0,
                "confidence": float(analysis.confidence) if analysis.confidence else 0.0,
                "risk_score": float(analysis.risk_score) if analysis.risk_score else 0.0,
                "reasoning": analysis.reasoning or "",
            },
            "title": analysis.title,
            "summary": analysis.summary,
            "industries": analysis.industries or [],
        }

        # 检查是否已存在 article
        from app.domain.entities.article import Article, StockRef

        existing_stmt = select(AnalysisArticle).where(
            AnalysisArticle.article_id == article_id,
            AnalysisArticle.deleted == "0",
        )
        existing_result = await self.session.execute(existing_stmt)
        existing = existing_result.scalar_one_or_none()

        if existing:
            # 更新已有 article
            existing.title = analysis.title
            existing.summary = analysis.summary
            existing.content = analysis.full_content or ""
            existing.analysis_data = analysis_data
            existing.status = "completed"
        else:
            # 创建新 article
            article = AnalysisArticle(
                article_id=article_id,
                title=analysis.title,
                summary=analysis.summary,
                content=analysis.full_content or "",
                event_type="other",
                raw_input=f"{analysis.stock_code} {analysis.stock_name}",
                user_id=analysis.user_id,
                article_type="stock_analysis",
                analysis_data=analysis_data,
                status="completed",
            )
            self.session.add(article)

            # 创建 ArticleStock 关联
            stock_ref = ArticleStock(
                id=uuid.uuid4().hex,
                article_id=article_id,
                stock_code=analysis.stock_code,
                stock_name=analysis.stock_name,
            )
            self.session.add(stock_ref)

        # 回写 article_id 到分析主表
        sa_stmt = select(StockAnalysisModel).where(StockAnalysisModel.analysis_id == analysis_id)
        sa_result = await self.session.execute(sa_stmt)
        sa_model = sa_result.scalar_one_or_none()
        if sa_model:
            sa_model.article_id = article_id

        await self.session.flush()
        await self.session.commit()
        return article_id
