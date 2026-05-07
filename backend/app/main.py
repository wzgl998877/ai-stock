import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import setup_logging
from app.infrastructure.ai.ai_service import AIService
from app.routers import analysis, knowledge, chat, sync, datasource, stock_data, watchlist, industry, auth

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    setup_logging()
    app.state.ai_service = AIService()

    # 初始化 LangGraph 分析工作流
    try:
        from app.infrastructure.workflow.graph.analysis_graph import build_analysis_graph
        from app.core.database import async_session

        analysis_graph = build_analysis_graph(session_factory=async_session, ai_service=app.state.ai_service)
        app.state.analysis_graph = analysis_graph
        logger.info("LangGraph 分析工作流初始化成功")
    except Exception as e:
        logger.warning("LangGraph 工作流初始化失败，将降级运行: %s", e)
        app.state.analysis_graph = None

    # 初始化个股分析工作流
    try:
        from app.infrastructure.workflow.graph.stock_analysis_graph import build_stock_analysis_graph

        stock_graph = build_stock_analysis_graph(ai_service=app.state.ai_service)
        app.state.stock_analysis_graph = stock_graph
        logger.info("LangGraph 个股分析工作流初始化成功")
    except Exception as e:
        logger.warning("LangGraph 个股分析工作流初始化失败: %s", e)
        app.state.stock_analysis_graph = None

    # 清理残留的 RUNNING 状态同步任务（进程重启后旧任务不可能仍在执行）
    try:
        from sqlalchemy import text
        async with async_session() as cleanup_session:
            result = await cleanup_session.execute(
                text(
                    "UPDATE t_sync_task SET status='failed', "
                    "error_message='进程重启，任务中断' "
                    "WHERE status='running'"
                )
            )
            await cleanup_session.commit()
            if result.rowcount > 0:
                logger.info("清理残留 RUNNING 任务: %d 条标记为 failed", result.rowcount)
    except Exception as e:
        logger.warning("清理残留任务失败（非致命）: %s", e)

    yield
    # Shutdown


app = FastAPI(
    title="AI Stock - AI 事件分析",
    version="0.1.0",
    description="模块一：AI 事件分析 & 行业知识库",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

access_logger = logging.getLogger("app.access")


@app.middleware("http")
async def log_requests(request: Request, call_next) -> Response:
    """HTTP 请求日志中间件：记录请求参数、响应状态码、返回报文、耗时。"""
    start_time = time.time()

    method = request.method
    path = request.url.path
    query_params = dict(request.query_params) if request.query_params else {}

    if query_params:
        logger.info("[%s] %s | query=%s", method, path, query_params)
    else:
        logger.info("[%s] %s", method, path)

    try:
        response = await call_next(request)
        status_code = response.status_code
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error("[%s] %s | 异常=%s | 耗时=%.3fs", method, path, e, elapsed)
        raise

    elapsed = time.time() - start_time

    # 尝试读取返回 body（仅非流式响应）
    resp_body = None
    if hasattr(response, "body"):
        try:
            resp_body = response.body.decode("utf-8")
            # 截断过长的 body，避免日志爆炸
            if len(resp_body) > 2000:
                resp_body = resp_body[:2000] + "...[truncated]"
        except Exception:
            pass

    log_kwargs = {"method": method, "path": path, "status": status_code, "elapsed": elapsed}
    if resp_body:
        log_kwargs["body"] = resp_body

    if status_code >= 500:
        if resp_body:
            access_logger.error("[%s] %s | status=%d | 耗时=%.3fs | 返回=%s", method, path, status_code, elapsed, resp_body)
        else:
            access_logger.error("[%s] %s | status=%d | 耗时=%.3fs", method, path, status_code, elapsed)
    elif status_code >= 400:
        if resp_body:
            logger.warning("[%s] %s | status=%d | 耗时=%.3fs | 返回=%s", method, path, status_code, elapsed, resp_body)
        else:
            logger.warning("[%s] %s | status=%d | 耗时=%.3fs", method, path, status_code, elapsed)
    else:
        if resp_body:
            logger.info("[%s] %s | status=%d | 耗时=%.3fs | 返回=%s", method, path, status_code, elapsed, resp_body)
        else:
            logger.info("[%s] %s | status=%d | 耗时=%.3fs", method, path, status_code, elapsed)

    return response

app.include_router(auth.router)
app.include_router(analysis.router)
app.include_router(knowledge.router)
app.include_router(chat.router)
app.include_router(sync.router)
app.include_router(datasource.router)
app.include_router(stock_data.router)
app.include_router(watchlist.router)
app.include_router(industry.router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    from app.core.logging import get_log_config

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        log_config=get_log_config(),
    )
