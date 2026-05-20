"""trace_context 模块单元测试"""

import contextvars
import pytest
from app.core.trace_context import (
    new_trace_id, get_trace_id, set_trace_id, clear_trace_id,
    push_span, pop_span, get_span_id, new_log_id,
)


@pytest.fixture(autouse=True)
def _clean_context():
    """每个测试前后清理上下文状态"""
    clear_trace_id()
    yield
    clear_trace_id()


class TestTraceId:
    def test_new_trace_id_returns_hex(self):
        tid = new_trace_id()
        assert len(tid) == 32
        assert all(c in "0123456789abcdef" for c in tid)

    def test_get_trace_id_default_empty(self):
        assert get_trace_id() == ""

    def test_set_and_get(self):
        set_trace_id("abc123")
        assert get_trace_id() == "abc123"

    def test_clear(self):
        set_trace_id("abc")
        clear_trace_id()
        assert get_trace_id() == ""


class TestSpanId:
    def test_default_empty(self):
        assert get_span_id() == ""

    def test_push_pop_single(self):
        sid = push_span("router")
        assert sid == "router-0"
        assert get_span_id() == "router-0"
        result = pop_span()
        assert result == ""
        assert get_span_id() == ""

    def test_nested_spans(self):
        push_span("http")
        assert get_span_id() == "http-0"

        push_span("ai_call")
        assert get_span_id() == "ai_call-1"

        pop_span()
        assert get_span_id() == "http-0"

        pop_span()
        assert get_span_id() == ""

    def test_pop_empty_stack(self):
        assert pop_span() == ""


class TestLogId:
    def test_unique(self):
        ids = {new_log_id() for _ in range(100)}
        assert len(ids) == 100

    def test_length(self):
        assert len(new_log_id()) == 8


class TestContextIsolation:
    def test_trace_id_isolated_between_contexts(self):
        set_trace_id("parent")

        def child_task():
            assert get_trace_id() == "parent"
            new_trace_id()
            return get_trace_id()

        ctx = contextvars.copy_context()
        child_tid = ctx.run(child_task)

        # 子上下文有自己的 trace_id，不影响父
        assert child_tid != "parent"
