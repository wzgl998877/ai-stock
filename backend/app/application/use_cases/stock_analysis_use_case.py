"""StockAnalysisUseCase — 个股多Agent分析用例，编排 SSE 流式输出"""

import asyncio
import logging
import time
import uuid
from typing import AsyncGenerator, Optional

from app.application.dtos.stock_analysis_dto import StockAnalysisConfigDTO
from app.domain.entities.article import Article, StockRef
from app.domain.entities.chat_session import ChatSession
from app.domain.entities.chat_message import ChatMessage
from app.domain.entities.stock_analysis import StockAnalysis
from app.domain.repositories.article_repo import ArticleRepository
from app.domain.repositories.chat_repo import ChatRepository
from app.domain.repositories.stock_analysis_repo import StockAnalysisRepository
from app.domain.services.analysis_parser import AnalysisParser
from app.domain.services.signal_extractor import SignalExtractor
from app.domain.value_objects.agent_type import AGENT_DISPLAY_NAMES
from app.infrastructure.ai.ai_service import AIService

logger = logging.getLogger(__name__)

# 超时配置（秒）
DEFAULT_TIMEOUT = 300
MAX_TIMEOUT = 600


class StockAnalysisUseCase:
    """个股多Agent分析用例"""

    def __init__(
        self,
        chat_repo: ChatRepository,
        ai_service: AIService,
        stock_analysis_graph=None,
        article_repo: Optional[ArticleRepository] = None,
        stock_analysis_repo: Optional[StockAnalysisRepository] = None,
    ):
        self.chat_repo = chat_repo
        self.ai_service = ai_service
        self.stock_analysis_graph = stock_analysis_graph
        self.article_repo = article_repo
        self.stock_analysis_repo = stock_analysis_repo
        self.parser = AnalysisParser()
        self.signal_extractor = SignalExtractor()

    async def execute(
        self,
        session_id: str,
        config: StockAnalysisConfigDTO,
    ) -> AsyncGenerator[dict, None]:
        """
        执行个股深度分析，SSE 流式返回。

        流程：初始化 → 创建分析记录 → 运行 LangGraph → 流式 yield 事件 → 解析结果 → 保存 → 同步到知识库

        流式输出机制：
        - 创建 sse_queue（SSE 事件队列）和 content_queue（内容 chunk 队列）
        - 后台任务运行 LangGraph，所有事件（agent_status、thinking 等）推入 sse_queue
        - 节点内部将 LLM 流式 content chunk 推入 content_queue
        - 主循环优先消费 content_queue 中的字符，实现逐字输出；同时消费 sse_queue 中的结构化事件
        """
        t_start = time.time()

        t0 = time.time()
        session = await self.chat_repo.get_session(session_id)
        logger.info("[耗时] 获取会话: %.3fs", time.time() - t0)
        if not session:
            yield {"type": "error", "data": "会话不存在"}
            return

        stock_code = config.stock_code
        stock_name = config.stock_name
        analysis_mode = config.analysis_mode

        # 1. 保存用户消息
        t0 = time.time()
        user_msg = ChatMessage(
            message_id=uuid.uuid4().hex,
            session_id=session_id,
            role="user",
            content=f"分析 {stock_name}({stock_code})",
            event_type="stock_analysis",
        )
        await self.chat_repo.add_message(user_msg)
        logger.info("[耗时] 保存用户消息: %.3fs", time.time() - t0)

        # 1.5 创建分析记录（写入新表 t_stock_analysis）
        t0 = time.time()
        analysis_id = uuid.uuid4().hex
        if self.stock_analysis_repo:
            try:
                sa = StockAnalysis(
                    analysis_id=analysis_id,
                    stock_code=stock_code,
                    stock_name=stock_name,
                    user_id=session.user_id,
                    analysis_mode=analysis_mode,
                    status="in_progress",
                    current_phase="analysts",
                    session_id=session_id,
                )
                await self.stock_analysis_repo.create(sa)
                analysis_id = sa.analysis_id
                await self.chat_repo.session.commit()
            except Exception as e:
                logger.warning("创建分析记录失败（不影响分析流程）: %s", e)
        logger.info("[耗时] 创建分析记录: %.3fs", time.time() - t0)

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

        # 超时保护
        graph_timed_out = False

        # === 双队列流式输出机制 ===
        sse_queue: asyncio.Queue = asyncio.Queue()    # 结构化 SSE 事件
        content_queue: asyncio.Queue = asyncio.Queue()  # LLM content chunks

        async def _run_graph_task():
            """后台运行 LangGraph，将事件推入 sse_queue。"""
            nonlocal accumulated, full_content
            t_graph_start = time.time()
            t_last_node = time.time()
            try:
                async for update in self.stock_analysis_graph.astream(
                    {
                        "stock_code": stock_code,
                        "stock_name": stock_name,
                        "analysis_mode": analysis_mode,
                        "messages": [],
                        "_content_queue": content_queue,
                    },
                    stream_mode="updates",
                ):
                    for node_name, state_update in update.items():
                        t_now = time.time()
                        logger.info("[耗时] 节点 [%s] 完成: %.3fs (距上个节点)", node_name, t_now - t_last_node)
                        t_last_node = t_now
                        accumulated.update(state_update)

                        # 获取当前 Agent 信息
                        current_agent = state_update.get("current_agent", node_name)
                        current_phase = state_update.get("current_phase", "analysts")
                        display_name = AGENT_DISPLAY_NAMES.get(current_agent, node_name)

                        # 发送 agent_status running
                        await sse_queue.put({
                            "type": "agent_status",
                            "data": {
                                "agent": current_agent,
                                "phase": current_phase,
                                "status": "running",
                            },
                        })

                        thinking_steps.append({
                            "step": current_agent,
                            "status": "running",
                            "message": f"{display_name}进行中...",
                        })
                        await sse_queue.put({
                            "type": "thinking",
                            "data": {
                                "step": current_agent,
                                "status": "running",
                                "message": f"{display_name}进行中...",
                            },
                        })

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
                                await sse_queue.put({
                                    "type": "agent_report",
                                    "data": {"agent": agent_id, "summary": summary},
                                })
                                full_content += f"\n## {AGENT_DISPLAY_NAMES.get(agent_id, agent_key)}\n{report}\n"

                                # 写入新表 detail
                                if self.stock_analysis_repo:
                                    try:
                                        await self.stock_analysis_repo.update_detail_by_agent(
                                            analysis_id, agent_id,
                                            status="done", summary=summary, full_report=report,
                                        )
                                    except Exception as e:
                                        logger.warning("更新agent detail失败: %s", e)

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
                            await sse_queue.put({"type": "decision", "data": decision})
                            full_content += f"\n## 最终决策\n{action} | 目标价: {decision['target_price']} | 置信度: {decision['confidence']*100:.0f}% | 风险评分: {decision['risk_score']*100:.0f}%\n{decision['reasoning']}"

                        # 发送 agent_status done
                        await sse_queue.put({
                            "type": "agent_status",
                            "data": {
                                "agent": current_agent,
                                "phase": current_phase,
                                "status": "done",
                            },
                        })

                        # 增量更新存档（每阶段完成时 → 写新表）
                        if self.stock_analysis_repo:
                            try:
                                await self.stock_analysis_repo.update_status(
                                    analysis_id, "in_progress", current_phase
                                )
                                await self.chat_repo.session.flush()
                            except Exception as e:
                                logger.warning("增量更新分析状态失败: %s", e)

                        thinking_steps.append({
                            "step": current_agent,
                            "status": "done",
                            "message": f"{display_name}完成",
                        })
                        await sse_queue.put({
                            "type": "thinking",
                            "data": {
                                "step": current_agent,
                                "status": "done",
                                "message": f"{display_name}完成",
                            },
                        })

                logger.info("[耗时] LangGraph 工作流总耗时: %.3fs", time.time() - t_graph_start)
                # 标记 graph 完成
                await sse_queue.put({"type": "graph_done", "data": None})
            except asyncio.TimeoutError:
                nonlocal graph_timed_out
                graph_timed_out = True
                logger.warning("StockAnalysisGraph 执行超时 (%ds)，保存部分结果", DEFAULT_TIMEOUT)
                await sse_queue.put({"type": "error", "data": "分析超时，已完成的部分结果已保存"})
                if self.stock_analysis_repo:
                    try:
                        await self.stock_analysis_repo.update_status(
                            analysis_id, "stopped", analysis_data.get("current_phase", "analysts")
                        )
                        await self.chat_repo.session.flush()
                    except Exception as e:
                        logger.warning("超时后更新记录状态失败: %s", e)
                await sse_queue.put({"type": "graph_done", "data": None})
            except Exception as e:
                logger.error("StockAnalysisGraph 执行异常: %s", e, exc_info=True)
                if self.stock_analysis_repo:
                    try:
                        await self.stock_analysis_repo.update_status(
                            analysis_id, "stopped", analysis_data.get("current_phase", "analysts")
                        )
                        await self.chat_repo.session.flush()
                    except Exception:
                        pass
                if full_content:
                    await sse_queue.put({"type": "error", "data": f"部分分析完成，但出现错误: {str(e)}"})
                else:
                    await sse_queue.put({"type": "error", "data": f"分析过程出错: {str(e)}"})
                await sse_queue.put({"type": "graph_done", "data": None})

        # 初始化 accumulated（在闭包中使用）
        accumulated = {}

        # 启动后台 graph 任务
        graph_task = asyncio.create_task(_run_graph_task())

        # 主循环：消费 sse_queue 和 content_queue
        graph_finished = False
        while not graph_finished:
            # 优先消费 content_queue 中的字符（实现逐字输出）
            while not content_queue.empty():
                try:
                    chunk = content_queue.get_nowait()
                    if chunk:
                        yield {"type": "content", "data": chunk}
                except asyncio.QueueEmpty:
                    break

            # 消费 sse_queue 中的结构化事件
            try:
                event = await asyncio.wait_for(sse_queue.get(), timeout=0.1)
                if event["type"] == "graph_done":
                    graph_finished = True
                else:
                    yield event
            except asyncio.TimeoutError:
                # 超时后再次检查 content_queue
                continue

        # graph 结束后，消费 content_queue 中可能剩余的 chunk
        while True:
            try:
                chunk = content_queue.get_nowait()
                if chunk:
                    yield {"type": "content", "data": chunk}
            except asyncio.QueueEmpty:
                break

        # 等待 graph 任务完成
        await graph_task

        # 3. 生成标题和摘要
        t0 = time.time()
        parse_result = self.parser.parse_stock_analysis(analysis_data)
        logger.info("[耗时] 解析标题/摘要: %.3fs", time.time() - t0)

        title = parse_result.title or f"{stock_name}深度分析"
        summary = parse_result.summary or f"{stock_name}多Agent深度分析报告"
        industries = parse_result.industry_names

        yield {"type": "title", "data": title}
        yield {"type": "summary", "data": summary}
        if industries:
            yield {"type": "industries", "data": industries}

        # 4. 保存 AI 消息
        t0 = time.time()
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
        logger.info("[耗时] 保存AI消息: %.3fs", time.time() - t0)

        # 4.5 更新分析结果到新表 + 同步到知识库
        t0 = time.time()
        if self.stock_analysis_repo:
            try:
                decision = analysis_data.get("decision", {})
                await self.stock_analysis_repo.update_result(
                    analysis_id,
                    title=title,
                    summary=summary,
                    full_content=full_content or "分析完成",
                    decision_action=decision.get("action"),
                    target_price=decision.get("target_price"),
                    confidence=decision.get("confidence"),
                    risk_score=decision.get("risk_score"),
                    reasoning=decision.get("reasoning"),
                    industries=industries,
                )
                # 同步到知识库 t_analysis_article
                await self.stock_analysis_repo.sync_to_article(analysis_id)
                await self.chat_repo.session.flush()
            except Exception as e:
                logger.warning("更新分析记录为完成状态失败: %s", e)

        await self.chat_repo.session.commit()
        logger.info("[耗时] 更新分析记录+commit: %.3fs", time.time() - t0)

        # 5. 完成
        yield {"type": "done", "data": ""}
        logger.info("[耗时] 个股分析总耗时: %.2fs", time.time() - t_start)
