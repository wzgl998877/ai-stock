"""链路追踪日志组件 — TraceFilter + TraceFormatter

TraceFilter: 将 trace_id / span_id / log_id / app_name 注入每条 LogRecord
TraceFormatter: 使用 [date] [app] [traceId] [logId] [spanId] ... 格式输出
"""

import logging

from app.core.trace_context import get_trace_id, get_span_id, new_log_id

TRACE_FORMAT = (
    "[%(asctime)s] [%(app_name)s] [%(trace_id)s] [%(log_id)s] "
    "[%(span_id)s] [%(threadName)s] [%(levelname)-5s] "
    "[%(name)s] [%(funcName)s] [%(lineno)d] => %(message)s"
)

TRACE_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class TraceFilter(logging.Filter):
    """将链路追踪字段注入 LogRecord，供 Formatter 使用"""

    def __init__(self, app_name: str = ""):
        super().__init__()
        self.app_name = app_name

    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = get_trace_id()
        record.span_id = get_span_id()
        record.log_id = new_log_id()
        record.app_name = self.app_name
        return True


class TraceFormatter(logging.Formatter):
    """链路追踪日志格式化器"""

    def __init__(self, fmt=None, datefmt=None):
        super().__init__(
            fmt or TRACE_FORMAT,
            datefmt=datefmt or TRACE_DATE_FORMAT,
        )
