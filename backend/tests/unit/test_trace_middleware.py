"""trace 中间件集成测试 — 验证 log_requests 中的 traceId 管理"""

import asyncio
import logging

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.trace_context import get_trace_id, clear_trace_id


@pytest.fixture(autouse=True)
def _clean_context():
    clear_trace_id()
    yield
    clear_trace_id()


@pytest.fixture
def app_with_trace():
    """创建一个带 traceId 管理的测试 FastAPI 应用"""
    from app.core.trace_context import new_trace_id, set_trace_id, push_span, pop_span

    app = FastAPI()

    @app.middleware("http")
    async def trace_middleware(request, call_next):
        trace_id = request.headers.get("x-trace-id", "").strip() or new_trace_id()
        set_trace_id(trace_id)
        push_span("http")
        try:
            response = await call_next(request)
        finally:
            pop_span()
            clear_trace_id()
        response.headers["X-Trace-ID"] = trace_id
        return response

    @app.get("/test")
    async def test_endpoint():
        return {"trace_id": get_trace_id()}

    return app


class TestTraceMiddlewareIntegration:
    def test_generates_trace_id(self, app_with_trace):
        client = TestClient(app_with_trace)
        resp = client.get("/test")
        assert resp.status_code == 200
        assert "X-Trace-ID" in resp.headers
        trace_id = resp.headers["X-Trace-ID"]
        assert len(trace_id) == 32

    def test_reuses_incoming_trace_id(self, app_with_trace):
        client = TestClient(app_with_trace)
        resp = client.get("/test", headers={"X-Trace-ID": "custom-123"})
        assert resp.headers["X-Trace-ID"] == "custom-123"

    def test_trace_available_in_handler(self, app_with_trace):
        client = TestClient(app_with_trace)
        resp = client.get("/test")
        body = resp.json()
        assert body["trace_id"] == resp.headers["X-Trace-ID"]

    def test_cleared_after_request(self, app_with_trace):
        client = TestClient(app_with_trace)
        client.get("/test")
        assert get_trace_id() == ""
