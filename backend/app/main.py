import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.trace_context import new_trace_id, set_trace_id, clear_trace_id, push_span, pop_span
from app.infrastructure.ai.ai_service import AIService
from app.routers import analysis, knowledge, chat, sync, datasource, stock_data, watchlist, industry, auth, search, event_radar

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    setup_logging()
    app.state.ai_service = AIService()

    # 初始化统一搜索服务（在图构建之前，以便注入到节点）
    _search_svc = None
    try:
        from app.infrastructure.search import create_search_service
        _search_svc = create_search_service()
        if _search_svc:
            app.state.search_service = _search_svc
            logger.info("统一搜索服务初始化成功 (providers: %s)",
                         [p.name for p in _search_svc._providers])
        else:
            app.state.search_service = None
            logger.info("未配置搜索 Key，搜索服务未启用")
    except Exception as e:
        logger.warning("搜索服务初始化失败: %s", e)
        app.state.search_service = None

    # 初始化 RAG 语义检索服务（Embedding + ChromaDB）
    _embedding_svc = None
    _vector_search_repo = None
    try:
        from app.core.database import async_session as _async_session  # noqa: F811

        if settings.rag_enabled:
            from app.infrastructure.vector.embedding_client import LocalEmbeddingService
            from app.infrastructure.vector.chroma_store import ChromaVectorStore
            from app.infrastructure.repositories.chroma_vector_search_repo import ChromaVectorSearchRepo

            _embedding_svc = LocalEmbeddingService(model_name=settings.rag_embedding_model)
            _chroma_store = ChromaVectorStore(persist_dir=settings.rag_vector_db_path)
            _vector_search_repo = ChromaVectorSearchRepo(_chroma_store)
            logger.info("RAG 初始化完成: model=%s, db=%s", settings.rag_embedding_model, settings.rag_vector_db_path)
        else:
            logger.info("RAG 已禁用 (rag_enabled=false)")
    except Exception as e:
        logger.warning("RAG 初始化失败，将降级运行: %s", e)
        _embedding_svc = None
        _vector_search_repo = None
    app.state.embedding_service = _embedding_svc
    app.state.vector_search_repo = _vector_search_repo

    # 初始化 LangGraph 分析工作流
    try:
        from app.infrastructure.workflow.graph.analysis_graph import build_analysis_graph
        from app.core.database import async_session

        analysis_graph = build_analysis_graph(
            session_factory=async_session,
            ai_service=app.state.ai_service,
            search_service=_search_svc,
            vector_search_repo=_vector_search_repo,
            embedding_service=_embedding_svc,
        )
        app.state.analysis_graph = analysis_graph
        logger.info("LangGraph 分析工作流初始化成功")
    except Exception as e:
        logger.warning("LangGraph 工作流初始化失败，将降级运行: %s", e)
        app.state.analysis_graph = None

    # 初始化个股分析工作流
    try:
        from app.infrastructure.workflow.graph.stock_analysis_graph import build_stock_analysis_graph

        stock_graph = build_stock_analysis_graph(
            ai_service=app.state.ai_service,
            search_service=_search_svc,
            vector_search_repo=_vector_search_repo,
            embedding_service=_embedding_svc,
        )
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

    # 注入股票名称映射（供事件雷达股票匹配使用）
    try:
        from sqlalchemy import text
        from app.domain.services.event_stock_matcher import set_stock_name_map
        async with async_session() as map_session:
            result = await map_session.execute(
                text("SELECT name, stock_code FROM t_stock WHERE is_active = 1")
            )
            name_map = {row[0]: row[1] for row in result.fetchall()}
            set_stock_name_map(name_map)
            logger.info("股票名称映射已注入: %d 条", len(name_map))
    except Exception as e:
        logger.warning("股票名称映射注入失败（非致命）: %s", e)

    # 初始化事件采集调度器（APScheduler）
    _event_scheduler = None
    try:
        from app.infrastructure.scheduler.event_crawler_scheduler import setup_scheduler
        _event_scheduler = setup_scheduler(
            session_factory=async_session,
            ai_service=app.state.ai_service,
            search_service=_search_svc,
            vector_search_repo=_vector_search_repo,
            embedding_service=_embedding_svc,
        )
        if _event_scheduler:
            _event_scheduler.start()
            logger.info("事件采集调度器已启动")
    except Exception as e:
        logger.warning("事件采集调度器初始化失败（非致命）: %s", e)

    yield
    # Shutdown
    if hasattr(app.state, "search_service") and app.state.search_service:
        await app.state.search_service._cache.close()
    if _event_scheduler:
        _event_scheduler.shutdown(wait=False)
        logger.info("事件采集调度器已关闭")


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
    # 链路追踪：从上游请求头读取或生成 traceId
    trace_id = request.headers.get("x-trace-id", "").strip() or new_trace_id()
    set_trace_id(trace_id)
    push_span("http")

    try:
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
                if len(resp_body) > 2000:
                    resp_body = resp_body[:2000] + "...[truncated]"
            except Exception:
                pass

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

        response.headers["X-Trace-ID"] = trace_id
        return response
    finally:
        pop_span()
        clear_trace_id()

app.include_router(auth.router)
app.include_router(analysis.router)
app.include_router(knowledge.router)
app.include_router(chat.router)
app.include_router(sync.router)
app.include_router(datasource.router)
app.include_router(stock_data.router)
app.include_router(watchlist.router)
app.include_router(industry.router)
app.include_router(search.router)
app.include_router(event_radar.router)

# 托管前端静态文件（与后端同端口）
_frontend_dist = Path(__file__).resolve().parent.parent / "dist"
if _frontend_dist.is_dir():
    from starlette.middleware.base import BaseHTTPMiddleware
    from fastapi.responses import FileResponse

    _api_prefixes = ("/api", "/health", "/docs", "/openapi", "/redoc")

    class SPAMiddleware(BaseHTTPMiddleware):
        """非 API 请求返回前端 SPA，API 请求正常放行"""

        async def dispatch(self, request, call_next):
            response = await call_next(request)
            if (
                request.method == "GET"
                and response.status_code == 404
                and not request.url.path.startswith(_api_prefixes)
            ):
                file = _frontend_dist / request.url.path.lstrip("/")
                if file.is_file():
                    return FileResponse(file)
                return FileResponse(_frontend_dist / "index.html")
            return response

    app.add_middleware(SPAMiddleware)
    app.mount("/assets", StaticFiles(directory=_frontend_dist / "assets"), name="assets")


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
