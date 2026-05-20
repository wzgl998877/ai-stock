"""trace_logging 模块单元测试"""

import logging
import re

from app.core.trace_context import set_trace_id, clear_trace_id, push_span, pop_span
from app.core.trace_logging import TraceFilter, TraceFormatter, TRACE_FORMAT


class TestTraceFilter:
    def test_injects_fields(self):
        set_trace_id("test-trace-123")
        push_span("unit")
        try:
            f = TraceFilter(app_name="test-app")
            record = logging.LogRecord("x", logging.INFO, "", 0, "hello", (), None)
            f.filter(record)
            assert record.trace_id == "test-trace-123"
            assert record.span_id == "unit-0"
            assert record.app_name == "test-app"
            assert len(record.log_id) == 8
        finally:
            clear_trace_id()

    def test_always_returns_true(self):
        f = TraceFilter()
        record = logging.LogRecord("x", logging.INFO, "", 0, "", (), None)
        assert f.filter(record) is True

    def test_empty_context(self):
        clear_trace_id()
        f = TraceFilter(app_name="app")
        record = logging.LogRecord("x", logging.INFO, "", 0, "msg", (), None)
        f.filter(record)
        assert record.trace_id == ""
        assert record.span_id == ""


class TestTraceFormatter:
    def test_format_output_pattern(self):
        set_trace_id("abc123")
        push_span("test")
        try:
            f = TraceFilter(app_name="myapp")
            fmt = TraceFormatter()
            record = logging.LogRecord(
                "app.module", logging.INFO, "file.py", 42, "hello world", (), None
            )
            f.filter(record)
            output = fmt.format(record)

            assert "[myapp]" in output
            assert "[abc123]" in output
            assert "[test-0]" in output
            assert record.log_id in output
            assert "[INFO ]" in output
            assert "[app.module]" in output
            assert "=> hello world" in output
        finally:
            clear_trace_id()

    def test_format_empty_context(self):
        clear_trace_id()
        f = TraceFilter(app_name="app")
        fmt = TraceFormatter()
        record = logging.LogRecord("x", logging.WARNING, "", 0, "msg", (), None)
        f.filter(record)
        output = fmt.format(record)
        assert "[]" in output


class TestSanitizeCompatibility:
    def test_trace_filter_then_sanitize(self):
        """验证 TraceFilter 与 _sanitize_filter 可兼容工作"""
        from app.core.logging import _sanitize_filter

        set_trace_id("trace-1")
        try:
            tf = TraceFilter(app_name="app")
            record = logging.LogRecord(
                "x", logging.INFO, "", 0,
                "api_key=sk-1234567890 secret=yes", (), None
            )
            # 先 TraceFilter，再 sanitize
            tf.filter(record)
            _sanitize_filter(record)

            # trace 字段保留
            assert record.trace_id == "trace-1"
            assert record.app_name == "app"
            # 消息已脱敏
            assert "sk-1234" not in record.getMessage()
            assert "****" in record.getMessage()
        finally:
            clear_trace_id()
