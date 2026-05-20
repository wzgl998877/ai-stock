"""链路追踪上下文 — 基于 contextvars 实现请求级 traceId / spanId 传播"""

import uuid
from contextvars import ContextVar

# ── 上下文变量 ──────────────────────────────────────────────
_trace_id: ContextVar[str] = ContextVar("trace_id", default="")
_span_stack: ContextVar[list[str]] = ContextVar("span_stack", default=None)


# ── traceId ────────────────────────────────────────────────
def new_trace_id() -> str:
    """生成新的 traceId（UUID4 hex，32 字符），同时设置到上下文"""
    tid = uuid.uuid4().hex
    _trace_id.set(tid)
    return tid


def get_trace_id() -> str:
    return _trace_id.get()


def set_trace_id(tid: str) -> None:
    _trace_id.set(tid)


def clear_trace_id() -> None:
    _trace_id.set("")
    _span_stack.set(None)


# ── spanId（栈式嵌套）──────────────────────────────────────
def push_span(name: str) -> str:
    """压入新 span，返回生成的 spanId（格式: name-序号）"""
    stack = _span_stack.get()
    if stack is None:
        stack = []
    span_id = f"{name}-{len(stack)}"
    stack.append(span_id)
    _span_stack.set(stack)
    return span_id


def pop_span() -> str:
    """弹出当前 span，返回恢复后的 spanId（栈空则返回空串）"""
    stack = _span_stack.get()
    if not stack:
        return ""
    stack.pop()
    _span_stack.set(stack if stack else None)
    return stack[-1] if stack else ""


def get_span_id() -> str:
    """返回当前 spanId（栈顶），无 span 时返回空串"""
    stack = _span_stack.get()
    return stack[-1] if stack else ""


# ── logId ──────────────────────────────────────────────────
def new_log_id() -> str:
    """生成每条日志的唯一 ID（UUID4 hex 前 8 位）"""
    return uuid.uuid4().hex[:8]
