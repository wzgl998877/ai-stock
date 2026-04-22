import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import setup_logging
from app.infrastructure.ai.ai_service import AIService
from app.routers import analysis, knowledge, chat

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

app.include_router(analysis.router)
app.include_router(knowledge.router)
app.include_router(chat.router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
