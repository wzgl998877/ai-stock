"""Chat 路由 — 会话 CRUD + 流式对话"""

import json
import logging
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.dtos.chat_dto import (
    CreateSessionRequest,
    SessionResponse,
    SessionListResponse,
    SessionDetailResponse,
    SendMessageRequest,
    MessageResponse,
)
from app.application.use_cases.chat_use_case import ChatUseCase
from app.core.database import get_db
from app.core.exceptions import InvalidInputError
from app.infrastructure.repositories.mysql_chat_repo import MySQLChatRepository
from app.infrastructure.repositories.mysql_article_repo import MySQLArticleRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])

USER_ID = "default"  # MVP 阶段固定用户


def _get_use_case(request: Request, db: AsyncSession) -> ChatUseCase:
    """统一构造 ChatUseCase，注入 ai_service + analysis_graph + stock_analysis_graph + article_repo"""
    repo = MySQLChatRepository(db)
    article_repo = MySQLArticleRepository(db)
    ai_service = request.app.state.ai_service
    analysis_graph = getattr(request.app.state, "analysis_graph", None)
    stock_analysis_graph = getattr(request.app.state, "stock_analysis_graph", None)
    return ChatUseCase(repo, ai_service, analysis_graph, stock_analysis_graph, article_repo)


async def _sse_stream(event_gen: AsyncGenerator, db: AsyncSession) -> AsyncGenerator[str, None]:
    """SSE 流式输出"""
    try:
        async for event in event_gen:
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
    except Exception:
        await db.rollback()
        raise


@router.post("/sessions", status_code=201, response_model=SessionResponse)
async def create_session(body: CreateSessionRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """创建新会话"""
    use_case = _get_use_case(request, db)
    # 支持个股分析会话
    session_type = getattr(body, 'session_type', 'event_analysis')
    config = getattr(body, 'config', None)
    event_type = body.event_type
    if event_type == "stock_analysis":
        session_type = "stock_analysis"
    session = await use_case.create_session(USER_ID, body.title, event_type, session_type, config)
    await db.commit()
    return SessionResponse(
        id=session.session_id,
        title=session.title or "",
        event_type=session.event_type,
        created_at=session.create_time.isoformat() if session.create_time else "",
        updated_at=session.update_time.isoformat() if session.update_time else "",
    )


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(request: Request, db: AsyncSession = Depends(get_db)):
    """列出用户的所有会话"""
    use_case = _get_use_case(request, db)
    sessions = await use_case.list_sessions(USER_ID)
    return SessionListResponse(
        sessions=[
            SessionResponse(
                id=s.session_id,
                title=s.title or "",
                event_type=s.event_type,
                created_at=s.create_time.isoformat() if s.create_time else "",
                updated_at=s.update_time.isoformat() if s.update_time else "",
            )
            for s in sessions
        ],
        total=len(sessions),
    )


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
async def get_session(session_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    """获取会话详情（含消息列表）"""
    use_case = _get_use_case(request, db)
    session = await use_case.get_session(session_id)
    if not session:
        raise InvalidInputError("会话不存在")

    return SessionDetailResponse(
        id=session.session_id,
        title=session.title or "",
        event_type=session.event_type,
        messages=[
            MessageResponse(
                id=m.message_id,
                role=m.role,
                content=m.content,
                thinking_steps=m.thinking_steps,
                event_type=m.event_type,
                created_at=m.create_time.isoformat() if m.create_time else "",
            )
            for m in session.messages
        ],
        created_at=session.create_time.isoformat() if session.create_time else "",
        updated_at=session.update_time.isoformat() if session.update_time else "",
    )


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    """删除会话"""
    use_case = _get_use_case(request, db)
    success = await use_case.delete_session(session_id)
    await db.commit()
    if not success:
        raise InvalidInputError("会话不存在")
    return {"status": "ok"}


@router.post("/sessions/{session_id}/stream")
async def stream_message(session_id: str, body: SendMessageRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """在指定会话中发送消息，SSE 流式返回"""
    if not body.content or not body.content.strip():
        raise InvalidInputError("请输入消息内容")

    use_case = _get_use_case(request, db)

    # 获取可选的 config（个股分析配置）
    config = getattr(body, 'config', None)

    return StreamingResponse(
        _sse_stream(use_case.stream_chat(session_id, body.content, body.event_type, config), db),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
