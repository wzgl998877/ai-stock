"""请求链路追踪中间件 — 纯 ASGI 实现

职责：
1. 从请求头 X-Trace-ID 读取或生成新的 traceId
2. 设置 contextvar 供下游日志使用
3. 响应头添加 X-Trace-ID
4. 请求结束后清理 contextvar
"""

from app.core.trace_context import new_trace_id, set_trace_id, clear_trace_id


class RequestIDMiddleware:
    """ASGI 中间件：为每个 HTTP/WebSocket 请求注入 traceId"""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        # 从上游请求头提取 traceId（支持跨服务传播）
        headers = dict(scope.get("headers", []))
        incoming = headers.get(b"x-trace-id", b"").decode("utf-8", errors="ignore").strip()
        trace_id = incoming or new_trace_id()
        set_trace_id(trace_id)

        async def send_with_trace_id(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"x-trace-id", trace_id.encode("utf-8")))
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, send_with_trace_id)
        finally:
            clear_trace_id()
