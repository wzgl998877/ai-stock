"""
存量迁移脚本：从 t_analysis_article.analysis_data JSON 拆分到 t_stock_analysis + t_stock_analysis_detail

用法（在 backend 目录下运行）：
    python -m scripts.migrate_analysis_data

幂等性：通过 article_id 关联，已迁移的记录不会重复创建。
"""

import asyncio
import json
import logging
import sys
import os
import uuid
from datetime import datetime
from decimal import Decimal

# 确保可以导入 app 模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.infrastructure.db.models import (
    AnalysisArticle,
    ArticleStock,
    StockAnalysisModel,
    StockAnalysisDetailModel,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# agent key → (agent_name, phase, display_order)
AGENT_KEY_MAP = {
    "market": ("market_analyst", "analysts", 0),
    "fundamentals": ("fundamentals_analyst", "analysts", 1),
    "news": ("news_analyst", "analysts", 2),
    "sentiment": ("sentiment_analyst", "analysts", 3),
}

DEBATE_AGENTS = [
    ("bull_researcher", "debate", 4),
    ("bear_researcher", "debate", 5),
    ("research_manager", "debate", 6),
]

TRADER_AGENTS = [
    ("trader", "trader", 7),
]

RISK_AGENTS = [
    ("risky_debator", "risk", 8),
    ("safe_debator", "risk", 9),
    ("neutral_debator", "risk", 10),
    ("risk_judge", "risk", 11),
]


async def migrate():
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # 查询所有 stock_analysis 类型的文章
        stmt = (
            select(AnalysisArticle)
            .where(
                AnalysisArticle.article_type == "stock_analysis",
                AnalysisArticle.deleted == "0",
            )
            .order_by(AnalysisArticle.create_time.asc())
        )
        result = await session.execute(stmt)
        articles = result.scalars().all()

        logger.info("找到 %d 条 stock_analysis 文章记录", len(articles))

        migrated = 0
        skipped = 0
        errors = 0

        for article in articles:
            article_id = article.article_id

            # 检查是否已迁移
            existing_stmt = select(StockAnalysisModel).where(
                StockAnalysisModel.article_id == article_id,
                StockAnalysisModel.deleted == "0",
            )
            existing = (await session.execute(existing_stmt)).scalar_one_or_none()
            if existing:
                skipped += 1
                continue

            ad = article.analysis_data or {}
            if not ad:
                logger.warning("文章 %s 无 analysis_data，跳过", article_id)
                skipped += 1
                continue

            # 获取关联的股票信息
            stock_stmt = select(ArticleStock).where(
                ArticleStock.article_id == article_id,
                ArticleStock.deleted == "0",
            )
            stock_result = await session.execute(stock_stmt)
            stock_ref = stock_result.scalars().first()

            stock_code = stock_ref.stock_code if stock_ref else ""
            stock_name = stock_ref.stock_name if stock_ref else ""

            if not stock_code:
                # 从 raw_input 尝试提取
                raw = article.raw_input or ""
                parts = raw.split()
                if len(parts) >= 1:
                    stock_code = parts[0]
                if len(parts) >= 2:
                    stock_name = parts[1]

            if not stock_code:
                logger.warning("文章 %s 无法确定股票代码，跳过", article_id)
                skipped += 1
                continue

            analysis_mode = ad.get("mode", "full")
            agents = ad.get("agents", {})
            decision = ad.get("decision", {})
            industries = ad.get("industries", [])

            # 确定状态
            if article.status == "completed":
                status = "completed"
                current_phase = "done"
            elif article.status == "stopped":
                status = "stopped"
                current_phase = ad.get("current_phase", "analysts")
            else:
                status = article.status or "completed"
                current_phase = "done"

            # 创建主记录
            analysis_id = uuid.uuid4().hex
            sa_model = StockAnalysisModel(
                analysis_id=analysis_id,
                stock_code=stock_code,
                stock_name=stock_name,
                user_id=article.user_id,
                analysis_mode=analysis_mode,
                status=status,
                current_phase=current_phase,
                title=article.title or ad.get("title", ""),
                summary=article.summary or ad.get("summary", ""),
                full_content=article.content or "",
                decision_action=decision.get("action") if decision else None,
                target_price=Decimal(str(decision.get("target_price", 0))) if decision and decision.get("target_price") else None,
                confidence=Decimal(str(decision.get("confidence", 0))) if decision and decision.get("confidence") else None,
                risk_score=Decimal(str(decision.get("risk_score", 0))) if decision and decision.get("risk_score") else None,
                reasoning=decision.get("reasoning") if decision else None,
                industries=industries if industries else None,
                article_id=article_id,
                data_source="",
            )
            session.add(sa_model)

            # 创建 detail 记录
            order = 0

            # 分析师阶段
            for key, val in agents.items():
                if not isinstance(val, dict):
                    continue
                mapping = AGENT_KEY_MAP.get(key)
                if not mapping:
                    continue
                agent_name, phase, _ = mapping

                detail = StockAnalysisDetailModel(
                    detail_id=uuid.uuid4().hex,
                    analysis_id=analysis_id,
                    agent_name=agent_name,
                    phase=phase,
                    status="done" if val.get("status") == "done" else "pending",
                    summary=val.get("summary", ""),
                    full_report=val.get("full_report", ""),
                    display_order=order,
                )
                session.add(detail)
                order += 1

            # 如果是 full 模式且有决策数据，补充辩论/交易员/风险阶段的 detail
            if analysis_mode == "full":
                for agent_name, phase, _ in DEBATE_AGENTS + TRADER_AGENTS + RISK_AGENTS:
                    detail = StockAnalysisDetailModel(
                        detail_id=uuid.uuid4().hex,
                        analysis_id=analysis_id,
                        agent_name=agent_name,
                        phase=phase,
                        status="done" if status == "completed" else "pending",
                        display_order=order,
                    )
                    session.add(detail)
                    order += 1

            try:
                await session.flush()
                migrated += 1
                logger.info("迁移成功: article_id=%s → analysis_id=%s (%s)", article_id, analysis_id, stock_name)
            except Exception as e:
                logger.error("迁移失败: article_id=%s, error=%s", article_id, e)
                await session.rollback()
                errors += 1

        # 最终提交
        try:
            await session.commit()
            logger.info("=== 迁移完成 ===")
            logger.info("总计: %d 条, 成功: %d, 跳过: %d, 失败: %d", len(articles), migrated, skipped, errors)
        except Exception as e:
            await session.rollback()
            logger.error("最终提交失败: %s", e)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(migrate())
