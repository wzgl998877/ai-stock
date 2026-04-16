from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.infrastructure.ai.ai_service import AIService
from app.routers import analysis


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app.state.ai_service = AIService()
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


@app.get("/health")
async def health_check():
    return {"status": "ok"}
