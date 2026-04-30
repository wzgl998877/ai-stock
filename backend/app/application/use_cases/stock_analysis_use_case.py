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
DEFAULT_TIMEOUT = 1200  # 20分钟（4分析师+辩论+风险+信号提取，含 AI 调用延迟）
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

                        # 跳过内部路由节点（msg_clear_*），不发送 status 事件
                        if node_name.startswith("msg_clear"):
                            continue

                        # 注意：stream_mode="updates" 只在节点完成后才 yield，
                        # 所以这里不发送 agent_status: "running"（会误导前端认为节点刚开始）。
                        # 只在节点完成时发送 "done" 状态。

                        # 初始化（防止后续引用未定义变量）
                        report_text = ""
                        agent_had_error = False  # 标记该 agent 是否内部报错

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
                                # 检测是否为节点内部错误（如 AI 调用失败）
                                is_err = "生成失败" in report or "调用失败" in report
                                analysis_data["agents"][agent_key] = {
                                    "status": "failed" if is_err else "done",
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
                                            status="failed" if is_err else "done",
                                            summary=summary, full_report=report,
                                        )
                                    except Exception as e:
                                        logger.warning("更新agent detail失败: %s", e)

                                # 如果当前节点正好是该分析师，记录错误状态
                                if current_agent == agent_id and is_err:
                                    agent_had_error = True

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
                                "stop_loss_price": state_update.get("stop_loss_price", 0.0),
                                "confidence": state_update.get("confidence", 0.0),
                                "risk_score": state_update.get("risk_score", 0.0),
                                "reasoning": state_update.get("reasoning", ""),
                            }
                            analysis_data["decision"] = decision
                            await sse_queue.put({"type": "decision", "data": decision})
                            full_content += f"\n## 最终决策\n{action} | 目标价: {decision['target_price']} | 置信度: {decision['confidence']*100:.0f}% | 风险评分: {decision['risk_score']*100:.0f}%\n{decision['reasoning']}"

                        # === 非 Analyst 阶段的 agent detail 写入 ===
                        if self.stock_analysis_repo and current_agent not in (
                            "market_analyst", "fundamentals_analyst",
                            "news_analyst", "sentiment_analyst",
                        ):
                            try:
                                report_text = ""
                                debate_data_val = None

                                # Debate 阶段：bull / bear
                                if current_agent == "bull_researcher":
                                    ds = state_update.get("investment_debate_state", {})
                                    report_text = ds.get("bull_arguments", "")
                                    if report_text:
                                        round_num = ds.get("round", 0)
                                        debate_data_val = {"round": round_num, "bull_argument": report_text}
                                        analysis_data["debate"]["bull_arguments"].append(report_text)
                                        await sse_queue.put({
                                            "type": "debate",
                                            "data": {
                                                "round": round_num,
                                                "agent": "bull_researcher",
                                                "stance": "bull",
                                                "argument": report_text,
                                            },
                                        })
                                        full_content += f"\n### 看多论据 (Round {round_num})\n{report_text}\n"

                                elif current_agent == "bear_researcher":
                                    ds = state_update.get("investment_debate_state", {})
                                    report_text = ds.get("bear_arguments", "")
                                    if report_text:
                                        round_num = ds.get("round", 0)
                                        debate_data_val = {"round": round_num, "bear_argument": report_text}
                                        analysis_data["debate"]["bear_arguments"].append(report_text)
                                        await sse_queue.put({
                                            "type": "debate",
                                            "data": {
                                                "round": round_num,
                                                "agent": "bear_researcher",
                                                "stance": "bear",
                                                "argument": report_text,
                                            },
                                        })
                                        full_content += f"\n### 看空论据 (Round {round_num})\n{report_text}\n"

                                elif current_agent == "research_manager":
                                    report_text = investment_plan or ""

                                elif current_agent == "trader":
                                    # full 模式取 trader_investment_plan，quick 模式取 reasoning
                                    report_text = trader_plan or state_update.get("reasoning", "")

                                elif current_agent == "risky_debator":
                                    rs = state_update.get("risk_debate_state", {})
                                    report_text = rs.get("risky_view", "")
                                    if report_text:
                                        round_num = rs.get("round", 0)
                                        debate_data_val = {"round": round_num, "risky_view": report_text}
                                        analysis_data["risk_debate"]["risky_view"] = report_text
                                        await sse_queue.put({
                                            "type": "debate",
                                            "data": {
                                                "round": round_num,
                                                "agent": "risky_debator",
                                                "stance": "risky",
                                                "argument": report_text,
                                            },
                                        })
                                        full_content += f"\n### 激进观点 (Round {round_num})\n{report_text}\n"

                                elif current_agent == "safe_debator":
                                    rs = state_update.get("risk_debate_state", {})
                                    report_text = rs.get("safe_view", "")
                                    if report_text:
                                        round_num = rs.get("round", 0)
                                        debate_data_val = {"round": round_num, "safe_view": report_text}
                                        analysis_data["risk_debate"]["safe_view"] = report_text
                                        await sse_queue.put({
                                            "type": "debate",
                                            "data": {
                                                "round": round_num,
                                                "agent": "safe_debator",
                                                "stance": "safe",
                                                "argument": report_text,
                                            },
                                        })
                                        full_content += f"\n### 保守观点 (Round {round_num})\n{report_text}\n"

                                elif current_agent == "neutral_debator":
                                    rs = state_update.get("risk_debate_state", {})
                                    report_text = rs.get("neutral_view", "")
                                    if report_text:
                                        round_num = rs.get("round", 0)
                                        debate_data_val = {"round": round_num, "neutral_view": report_text}
                                        analysis_data["risk_debate"]["neutral_view"] = report_text
                                        await sse_queue.put({
                                            "type": "debate",
                                            "data": {
                                                "round": round_num,
                                                "agent": "neutral_debator",
                                                "stance": "neutral",
                                                "argument": report_text,
                                            },
                                        })
                                        full_content += f"\n### 中立观点 (Round {round_num})\n{report_text}\n"

                                elif current_agent == "risk_judge":
                                    # risk_judge 将裁决内容追加到 messages
                                    new_msgs = state_update.get("messages", [])
                                    judge_msg = next(
                                        (m for m in (new_msgs or []) if m.get("agent") == "risk_judge"),
                                        None,
                                    )
                                    if judge_msg:
                                        report_text = judge_msg.get("content", "")
                                        full_content += f"\n## 风险裁决\n{report_text}\n"

                                # 写入 detail 记录
                                if report_text:
                                    summary = report_text[:100] + ("..." if len(report_text) > 100 else "")
                                    # 判断是否为错误报告
                                    is_err = "生成失败" in report_text or "调用失败" in report_text
                                    if is_err:
                                        agent_had_error = True
                                    kwargs = {
                                        "status": "failed" if is_err else "done",
                                        "summary": summary,
                                        "full_report": report_text,
                                    }
                                    if debate_data_val:
                                        kwargs["debate_data"] = debate_data_val
                                    await self.stock_analysis_repo.update_detail_by_agent(
                                        analysis_id, current_agent, **kwargs,
                                    )
                                    # 同时推送 agent_report SSE 事件
                                    await sse_queue.put({
                                        "type": "agent_report",
                                        "data": {"agent": current_agent, "summary": summary, "full_report": report_text},
                                    })
                            except Exception as e:
                                logger.warning("更新agent detail失败 [%s]: %s", current_agent, e)

                        # 发送 agent_status done/failed（报错也继续执行，只记录状态）
                        agent_done_status = "failed" if agent_had_error else "done"
                        await sse_queue.put({
                            "type": "agent_status",
                            "data": {
                                "agent": current_agent,
                                "phase": current_phase,
                                "status": agent_done_status,
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
                            "status": agent_done_status,
                            "message": f"{display_name}{'失败（继续执行）' if agent_had_error else '完成'}",
                        })
                        await sse_queue.put({
                            "type": "thinking",
                            "data": {
                                "step": current_agent,
                                "status": agent_done_status,
                                "message": f"{display_name}{'失败（继续执行）' if agent_had_error else '完成'}",
                            },
                        })

                logger.info("[耗时] LangGraph 工作流总耗时: %.3fs", time.time() - t_graph_start)

                # === 在后台任务中完成保存，不依赖 SSE 连接 ===
                # 解析标题/摘要
                t0 = time.time()
                parse_result = self.parser.parse_stock_analysis(analysis_data)
                logger.info("[耗时] 解析标题/摘要: %.3fs", time.time() - t0)

                title = parse_result.title or f"{stock_name}深度分析"
                summary = parse_result.summary or f"{stock_name}多Agent深度分析报告"
                industries = parse_result.industry_names

                # 保存 AI 消息到聊天记录（允许失败，不影响分析结果保存）
                t0 = time.time()
                try:
                    ai_msg = ChatMessage(
                        message_id=uuid.uuid4().hex,
                        session_id=session_id,
                        role="assistant",
                        content=(full_content or "分析完成")[:60000],  # 截断防止超限
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
                except Exception as e:
                    logger.warning("保存AI消息失败（不影响分析结果）: %s", e)
                    try:
                        await self.chat_repo.session.rollback()
                    except Exception:
                        pass

                # 更新分析结果到新表 + 同步到知识库（关键路径，必须成功）
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
                            stop_loss_price=decision.get("stop_loss_price"),
                            confidence=decision.get("confidence"),
                            risk_score=decision.get("risk_score"),
                            reasoning=decision.get("reasoning"),
                            industries=industries,
                        )
                        await self.stock_analysis_repo.sync_to_article(analysis_id)
                        await self.chat_repo.session.commit()
                    except Exception as e:
                        logger.warning("更新分析记录为完成状态失败: %s", e)
                        try:
                            await self.stock_analysis_repo.session.rollback()
                        except Exception:
                            pass

                logger.info("[耗时] 更新分析记录+commit: %.3fs", time.time() - t0)

                # 将 title/summary/industries 推送到 SSE（主循环会 yield 给客户端）
                await sse_queue.put({"type": "title", "data": title})
                await sse_queue.put({"type": "summary", "data": summary})
                if industries:
                    await sse_queue.put({"type": "industries", "data": industries})

                logger.info("[耗时] 个股分析总耗时: %.2fs", time.time() - t_start)
                # 标记 graph 完成
                await sse_queue.put({"type": "graph_done", "data": None})
            except asyncio.TimeoutError:
                nonlocal graph_timed_out
                graph_timed_out = True
                logger.warning("StockAnalysisGraph 执行超时 (%ds)，保存部分结果", DEFAULT_TIMEOUT)
                await sse_queue.put({"type": "error", "data": "分析超时，已完成的部分结果已保存"})
                if self.stock_analysis_repo:
                    try:
                        await self.chat_repo.session.rollback()
                        await self.stock_analysis_repo.update_status(
                            analysis_id, "stopped", analysis_data.get("current_phase", "analysts")
                        )
                        await self.chat_repo.session.commit()
                        logger.info("超时后已保存部分结果（状态: stopped）")
                    except Exception as e:
                        logger.warning("超时后更新记录状态失败: %s", e)
                        try:
                            await self.chat_repo.session.rollback()
                        except Exception:
                            pass
                await sse_queue.put({"type": "graph_done", "data": None})
            except Exception as e:
                logger.error("StockAnalysisGraph 执行异常: %s", e, exc_info=True)
                if self.stock_analysis_repo:
                    try:
                        # 先 rollback 清除失败的事务，再开启新事务更新状态
                        await self.chat_repo.session.rollback()
                        await self.stock_analysis_repo.update_status(
                            analysis_id, "stopped", analysis_data.get("current_phase", "analysts")
                        )
                        await self.chat_repo.session.commit()
                        logger.info("异常后已保存部分结果（状态: stopped）")
                    except Exception as ex:
                        logger.warning("异常后更新记录状态失败: %s", ex)
                        try:
                            await self.chat_repo.session.rollback()
                        except Exception:
                            pass
                if full_content:
                    await sse_queue.put({"type": "error", "data": f"部分分析完成，但出现错误: {str(e)}"})
                else:
                    await sse_queue.put({"type": "error", "data": f"分析过程出错: {str(e)}"})
                await sse_queue.put({"type": "graph_done", "data": None})
            except asyncio.CancelledError:
                logger.warning("graph_task 被取消（可能因超时或 SSE 断开）")
                if self.stock_analysis_repo:
                    try:
                        await self.stock_analysis_repo.update_status(
                            analysis_id, "stopped", analysis_data.get("current_phase", "analysts")
                        )
                        await self.chat_repo.session.commit()
                        logger.info("取消后已保存部分结果")
                    except Exception:
                        pass
                await sse_queue.put({"type": "error", "data": "分析被中断"})
                await sse_queue.put({"type": "graph_done", "data": None})

        # 初始化 accumulated（在闭包中使用）
        accumulated = {}

        # 启动后台 graph 任务
        graph_task = asyncio.create_task(_run_graph_task())
        t_main_start = time.time()

        # 主循环：消费 sse_queue 和 content_queue，带总超时保护
        graph_finished = False
        while not graph_finished:
            # 超时保护：超过 DEFAULT_TIMEOUT 秒强制结束
            if time.time() - t_main_start > DEFAULT_TIMEOUT:
                logger.warning("主循环等待超时 (%ds)，强制取消 graph_task", DEFAULT_TIMEOUT)
                graph_task.cancel()
                try:
                    await graph_task
                except asyncio.CancelledError:
                    pass
                yield {"type": "error", "data": f"分析超时（{DEFAULT_TIMEOUT}s），已取消"}
                break

            # 先消费 sse_queue（结构化事件），确保 agent 状态及时更新
            while not sse_queue.empty():
                try:
                    event = sse_queue.get_nowait()
                    if event["type"] == "graph_done":
                        graph_finished = True
                        break
                    yield event
                except asyncio.QueueEmpty:
                    break

            if graph_finished:
                break

            # 再消费 content_queue 中的流式文本
            content_drained = 0
            while content_drained < 5:  # 每轮最多消费 5 个 chunk，避免长时间阻塞 sse_queue
                try:
                    chunk = content_queue.get_nowait()
                    if chunk:
                        yield {"type": "content", "data": chunk}
                    content_drained += 1
                except asyncio.QueueEmpty:
                    break

            # 两个队列都空时，等待新事件
            if sse_queue.empty() and content_queue.empty():
                try:
                    event = await asyncio.wait_for(sse_queue.get(), timeout=0.1)
                    if event["type"] == "graph_done":
                        graph_finished = True
                    else:
                        yield event
                except asyncio.TimeoutError:
                    continue

        # graph 结束后，消费 content_queue 中可能剩余的 chunk
        while True:
            try:
                chunk = content_queue.get_nowait()
                if chunk:
                    yield {"type": "content", "data": chunk}
            except asyncio.QueueEmpty:
                break

        # 等待 graph 任务完成（保存已在后台任务中完成，不依赖 SSE 连接）
        if not graph_task.done():
            try:
                await asyncio.wait_for(graph_task, timeout=10)
            except asyncio.TimeoutError:
                logger.warning("等待 graph_task 完成超时，强制取消")
                graph_task.cancel()
                try:
                    await graph_task
                except asyncio.CancelledError:
                    pass

        # 5. 完成
        yield {"type": "done", "data": ""}
