"""意图路由器测试（specs/010 T004）：规则命中 / LLM 解析 / chat 兜底 / 降级链。

规则层用真实注册的工具（run_chanlun 等 P1 三件套）；LLM 层 patch
``AIService.tool_call``（intent_router 函数内 import，patch 源模块即生效）。
"""

import pytest

import app.infrastructure.ai.ai_service as ai_module
from app.application.wechat.intent_router import (
    IntentResult,
    build_help_text,
    resolve_intent,
)

pytestmark = pytest.mark.asyncio


def _tool_call(name: str, arguments: str = "{}") -> dict:
    return {
        "tool_calls": [
            {"id": "c1", "type": "function",
             "function": {"name": name, "arguments": arguments}}
        ]
    }


# ---------------------------------------------------------------------------
# 1) 规则层（不依赖 LLM，spec FR-005）
# ---------------------------------------------------------------------------

async def test_pattern_exact_hit():
    r = await resolve_intent("跑缠论", [])
    assert r.tool_name == "run_chanlun" and r.via == "pattern"


async def test_pattern_with_stock_code():
    r = await resolve_intent("缠论 002940", [])
    assert r.tool_name == "run_chanlun"
    assert r.params.get("codes_str") == "002940"


async def test_pattern_query_commands():
    for text in ("缠论状态", "执行记录", "指令记录"):
        r = await resolve_intent(text, [])
        assert r.tool_name in ("chanlun_status", "cmd_history")
        assert r.via == "pattern"


# ---------------------------------------------------------------------------
# 2) LLM 层（FR-006）
# ---------------------------------------------------------------------------

async def test_llm_resolves_natural_language(monkeypatch):
    class FakeAI:
        async def tool_call(self, **kw):
            assert kw["tools"][0]["function"]["name"] == "run_chanlun"  # schema 已导出
            return _tool_call("run_chanlun", '{"codes": ["002940"]}')

    monkeypatch.setattr(ai_module, "AIService", FakeAI)
    r = await resolve_intent("帮我把 002940 的缠论算一下", [])
    assert r.tool_name == "run_chanlun" and r.via == "llm"
    assert r.params == {"codes": ["002940"]}


async def test_llm_chat_fallback_for_chitchat(monkeypatch):
    class FakeAI:
        async def tool_call(self, **kw):
            return _tool_call("chat")

    monkeypatch.setattr(ai_module, "AIService", FakeAI)
    r = await resolve_intent("今天天气不错", [])
    assert r.tool_name == "chat"
    assert "指令" in r.reply_text  # HELP 引导（US3 场景3）


async def test_llm_unknown_tool_name_guarded(monkeypatch):
    """LLM 幻觉出未注册工具 → 回帮助，不得执行（research D2 护栏）。"""

    class FakeAI:
        async def tool_call(self, **kw):
            return _tool_call("no_such_tool")

    monkeypatch.setattr(ai_module, "AIService", FakeAI)
    r = await resolve_intent("随便来点啥", [])
    assert r.tool_name is None and r.reply_text


# ---------------------------------------------------------------------------
# 3) 降级链（FR-008：LLM 不可用 → 规则仍可达，未中回带提示的帮助）
# ---------------------------------------------------------------------------

async def test_llm_failure_degrades_gracefully(monkeypatch):
    class BrokenAI:
        async def tool_call(self, **kw):
            raise RuntimeError("LLM down")

    monkeypatch.setattr(ai_module, "AIService", BrokenAI)
    # 规则可命中的指令不受影响
    r1 = await resolve_intent("执行记录", [])
    assert r1.via == "pattern" and r1.tool_name == "cmd_history"

    # 规则也不中的 → 降级帮助 + 告知（US3 场景4）
    r2 = await resolve_intent("帮我把缠论跑一遍", [])
    assert r2.via == "fallback"
    assert "仅支持上述精确指令" in r2.reply_text


def test_help_text_lists_registered_tools():
    text = build_help_text()
    assert "跑缠论" in text and "缠论状态" in text and "执行记录" in text
