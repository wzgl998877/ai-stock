import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.infrastructure.ai.ai_service import StreamChunk
from app.infrastructure.workflow.nodes.stock_tool_runner import collect_report_with_tool_continuation
from app.application.use_cases.stock_analysis_use_case import _is_invalid_agent_report, _safe_agent_report


class _FakeToolAwareAI:
    def __init__(self):
        self.calls = 0
        self.max_tokens_seen = []

    async def stream_chat_with_tools(self, **kwargs):
        self.calls += 1
        self.max_tokens_seen.append(kwargs.get("max_tokens"))
        if self.calls == 1:
            yield StreamChunk(
                "tool_calls",
                "",
                tool_calls=[{
                    "id": "call_1",
                    "type": "function",
                    "function": {"name": "get_stock_news", "arguments": '{"code":"605117"}'},
                }],
            )
            return
        yield StreamChunk("content", "情绪分析报告")


@pytest.mark.asyncio
async def test_collect_report_continues_when_final_stage_requests_tool():
    ai = _FakeToolAwareAI()
    messages = [{"role": "user", "content": "分析情绪"}]
    queue = MagicMock()
    queue.put = AsyncMock()

    with patch(
        "app.infrastructure.workflow.nodes.stock_tool_runner.TOOL_FUNCTION_MAP",
        {"get_stock_news": lambda code: f"新闻数据:{code}"},
    ):
        report, extra_calls = await collect_report_with_tool_continuation(
            ai_service=ai,
            messages=messages,
            tools_schema=[],
            agent_name="sentiment_analyst",
            content_queue=queue,
        )

    assert report == "情绪分析报告"
    assert extra_calls == 1
    assert ai.calls == 2
    assert ai.max_tokens_seen == [100000, 100000]
    tool_message = next(msg for msg in messages if msg["role"] == "tool")
    assert "新闻数据:605117" in tool_message["content"]
    queue.put.assert_awaited_once_with("情绪分析报告")


@pytest.mark.asyncio
async def test_collect_report_rejects_dsml_as_report():
    class _DSMLAI:
        async def stream_chat_with_tools(self, **kwargs):
            yield StreamChunk("content", "<｜｜DSML｜｜tool_calls></｜｜DSML｜｜tool_calls>")

    report, extra_calls = await collect_report_with_tool_continuation(
        ai_service=_DSMLAI(),
        messages=[{"role": "user", "content": "分析"}],
        tools_schema=[],
        agent_name="sentiment_analyst",
        max_additional_tool_rounds=0,
    )

    assert extra_calls == 0
    assert "生成失败" in report
    assert "DSML" not in report


def test_stock_analysis_use_case_marks_dsml_report_invalid():
    dsml = "<｜｜DSML｜｜tool_calls>xxx</｜｜DSML｜｜tool_calls>"

    assert _is_invalid_agent_report(dsml)
    safe_report = _safe_agent_report(dsml, "情绪分析师")
    assert "生成失败" in safe_report
    assert "<｜｜DSML｜｜" not in safe_report
