"""StockAnalysisUseCase — 个股多Agent分析用例，编排 SSE 流式输出"""

import logging
import time
import uuid
from typing import AsyncGenerator, Optional

from app.application.dtos.stock_analysis_dto import StockAnalysisConfigDTO
from app.domain.entities.chat_session import ChatSession
from app.domain.entities.chat_message import ChatMessage
from app.domain.repositories.chat_repo import ChatRepository
from app.domain.services.analysis_parser import AnalysisParser
from app.domain.services.signal_extractor import SignalExtractor
from app.domain.value_objects.agent_type import AGENT_DISPLAY_NAMES
from app.infrastructure.ai.ai_service import AIService

logger = logging.getLogger(__name__)


class StockAnalysisUseCase:
    """个股多Agent分析用例"""

    def __init__(self, chat_repo: ChatRepository, ai_service: AIService, stock_analysis_graph=None):
        self.chat_repo = chat_repo
        self.ai_service = ai_service
        self.stock_analysis_graph = stock_analysis_graph
        self.parser = AnalysisParser()
        self.signal_extractor = SignalExtractor()

    async def execute(
        self,
        session_id: str,
        config: StockAnalysisConfigDTO,
    ) -> AsyncGenerator[dict, None]:
        """
        执行个股深度分析，SSE 流式返回。

        流程：初始化 → 运行 LangGraph → 流式 yield 事件 → 解析结果 → 保存
        """
        t_start = time.time()

        session = await self.chat_repo.get_session(session_id)
        if not session:
            yield {"type": "error", "data": "会话不存在"}
            return

        stock_code = config.stock_code
        stock_name = config.stock_name
        analysis_mode = config.analysis_mode

        # 1. 保存用户消息
        user_msg = ChatMessage(
            message_id=uuid.uuid4().hex,
            session_id=session_id,
            role="user",
            content=f"分析 {stock_name}({stock_code})",
            event_type="stock_analysis",
        )
        await self.chat_repo.add_message(user_msg)

        # 2. 运行 StockAnalysisGraph
        thinking_steps = []
        full_content = ""
        analysis_data = {
            "stock_code": stock_code,
            "stock_name": stock_name,
            "analysis_mode": analysis_mode,
            "agents": {},
            "debate": {"rounds": 0, "bull_arguments": [], "bear_arguments": []},
            "risk_debate": {},
            "decision": {},
        }

        if not self.stock_analysis_graph:
            yield {"type": "error", "data": "分析工作流未初始化"}
            return

        try:
            # 使用 astream 获取节点级更新
            accumulated = {}
            async for update in self.stock_analysis_graph.astream(
                {
                    "stock_code": stock_code,
                    "stock_name": stock_name,
                    "analysis_mode": analysis_mode,
                    "messages": [],
                },
                stream_mode="updates",
            ):
                for node_name, state_update in update.items():
                    accumulated.update(state_update)

                    # 获取当前 Agent 信息
                    current_agent = state_update.get("current_agent", node_name)
                    current_phase = state_update.get("current_phase", "analysts")
                    display_name = AGENT_DISPLAY_NAMES.get(current_agent, node_name)

                    # 发送 agent_status running
                    yield {
                        "type": "agent_status",
                        "data": {
                            "agent": current_agent,
                            "phase": current_phase,
                            "status": "running",
                        },
                    }

                    thinking_steps.append({
                        "step": current_agent,
                        "status": "running",
                        "message": f"{display_name}进行中...",
                    })
                    yield {
                        "type": "thinking",
                        "data": {
                            "step": current_agent,
                            "status": "running",
                            "message": f"{display_name}进行中...",
                        },
                    }

                    # 提取各Agent报告
                    agent_reports = {
                        "market_report": ("market", "market_analyst"),
                        "fundamentals_report": ("fundamentals", "fundamentals_analyst"),
                        "news_report": ("news", "news_analyst"),
                        "sentiment_report": ("sentiment", "sentiment_analyst"),
                    }

                    for field_name, (agent_key, agent_id) in agent_reports.items():
                        report = state_update.get(field_name)
                        if report:
                            summary = report[:100] + ("..." if len(report) > 100 else "")
                            analysis_data["agents"][agent_key] = {
                                "status": "done",
                                "summary": summary,
                                "full_report": report,
                            }
                            yield {
                                "type": "agent_report",
                                "data": {"agent": agent_id, "summary": summary},
                            }
                            full_content += f"\n## {AGENT_DISPLAY_NAMES.get(agent_id, agent_key)}\n{report}\n"

                    # 提取辩论和风险辩论
                    investment_plan = state_update.get("investment_plan")
                    if investment_plan:
                        full_content += f"\n## 投资计划\n{investment_plan}\n"
                        analysis_data["debate"]["investment_plan"] = investment_plan

                    trader_plan = state_update.get("trader_investment_plan")
                    if trader_plan:
                        full_content += f"\n## 交易建议\n{trader_plan}\n"

                    # 提取结构化决策
                    action = state_update.get("action")
                    if action:
                        decision = {
                            "action": action,
                            "target_price": state_update.get("target_price", 0.0),
                            "confidence": state_update.get("confidence", 0.0),
                            "risk_score": state_update.get("risk_score", 0.0),
                            "reasoning": state_update.get("reasoning", ""),
                        }
                        analysis_data["decision"] = decision
                        yield {"type": "decision", "data": decision}
                        full_content += f"\n## 最终决策\n{action} | 目标价: {decision['target_price']} | 置信度: {decision['confidence']*100:.0f}% | 风险评分: {decision['risk_score']*100:.0f}%\n{decision['reasoning']}"

                    # 发送 agent_status done
                    yield {
                        "type": "agent_status",
                        "data": {
                            "agent": current_agent,
                            "phase": current_phase,
                            "status": "done",
                        },
                    }

                    thinking_steps.append({
                        "step": current_agent,
                        "status": "done",
                        "message": f"{display_name}完成",
                    })
                    yield {
                        "type": "thinking",
                        "data": {
                            "step": current_agent,
                            "status": "done",
                            "message": f"{display_name}完成",
                        },
                    }

        except Exception as e:
            logger.error("StockAnalysisGraph 执行失败: %s", e, exc_info=True)
            yield {"type": "error", "data": f"分析过程出错: {str(e)}"}

        # 3. 生成标题和摘要
        parse_result = self.parser.parse_stock_analysis(analysis_data)

        title = parse_result.title or f"{stock_name}深度分析"
        summary = parse_result.summary or f"{stock_name}多Agent深度分析报告"
        industries = parse_result.industry_names

        yield {"type": "title", "data": title}
        yield {"type": "summary", "data": summary}
        if industries:
            yield {"type": "industries", "data": industries}

        # 4. 保存 AI 消息
        ai_msg = ChatMessage(
            message_id=uuid.uuid4().hex,
            session_id=session_id,
            role="assistant",
            content=full_content or "分析完成",
            thinking_steps=thinking_steps or None,
            event_type="stock_analysis",
            agent_data={
                "current_agent": accumulated.get("current_agent", ""),
                "current_phase": accumulated.get("current_phase", "done"),
                "agent_statuses": {},
            },
        )
        await self.chat_repo.add_message(ai_msg)
        await self.chat_repo.session.commit()

        # 5. 完成
        yield {"type": "done", "data": ""}
        logger.info("[耗时] 个股分析总耗时: %.2fs", time.time() - t_start)
