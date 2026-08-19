import asyncio
from typing import List, Optional
from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.config import settings
from app.database import get_live_portfolio_data
from app.llm_provider import llm_provider
from app.memory import session_manager
from app.style_analyzer import STYLE_PROMPT_DIRECTIVES, style_analyzer

router = APIRouter(prefix="/api")


class IncomingChatMessage(BaseModel):
    role: str  # 'user' or 'assistant'
    content: str


class ChatRequestPayload(BaseModel):
    session_id: Optional[str] = None
    messages: Optional[List[IncomingChatMessage]] = None
    message: Optional[str] = None  # Single message convenience


class ChatResponsePayload(BaseModel):
    session_id: str
    reply: str
    user_style: str
    style_description: str
    model: str


@router.get("/health")
def health():
    data = get_live_portfolio_data(force_refresh=True)
    return {
        "status": "healthy",
        "provider": settings.LLM_PROVIDER,
        "model": settings.GEMINI_MODEL if settings.LLM_PROVIDER == "gemini" else settings.GROQ_MODEL,
        "has_gemini_key": bool(settings.GEMINI_API_KEY),
        "has_groq_key": bool(settings.GROQ_API_KEY),
        "db_connected": bool(data.get("profile")),
        "ai_facts_count": len(data.get("ai_facts", [])),
        "active_sessions_count": len(session_manager.sessions),
    }


@router.get("/debug-db")
def debug_db():
    import traceback
    from app.database import fetch_from_postgres, fetch_from_rest_api, get_db_connection
    
    postgres_err = None
    pg_data = None
    import psycopg2
    try:
        uri = f"postgresql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}?sslmode=require"
        conn = psycopg2.connect(uri, connect_timeout=10)
        conn.close()
        pg_data = fetch_from_postgres()
    except Exception as e:
        postgres_err = traceback.format_exc()

    rest_err = None
    rest_data = None
    try:
        rest_data = fetch_from_rest_api()
    except Exception as e:
        rest_err = traceback.format_exc()

    return {
        "db_host": settings.DB_HOST,
        "db_name": settings.DB_NAME,
        "db_user": settings.DB_USER,
        "portfolio_be_url": settings.PORTFOLIO_BE_URL,
        "postgres_error": postgres_err,
        "has_pg_profile": bool(pg_data and pg_data.get("profile")),
        "pg_ai_facts": pg_data.get("ai_facts") if pg_data else [],
        "rest_error": rest_err,
        "has_rest_profile": bool(rest_data and rest_data.get("profile")),
        "rest_ai_facts": rest_data.get("ai_facts") if rest_data else [],
    }


@router.get("/suggestions")
def get_suggestions():
    return {
        "suggestions": [
            "Kinh nghiệm làm việc & năng lực của Khoa?",
            "Các dự án nổi bật mà Khoa đã thực hiện?",
            "Khoa sử dụng những công nghệ Backend & AI nào?",
            "Làm thế nào để liên hệ và hợp tác với Khoa?",
        ]
    }


@router.post("/chat", response_model=ChatResponsePayload)
async def chat_endpoint(payload: ChatRequestPayload, background_tasks: BackgroundTasks):
    session = session_manager.get_or_create_session(payload.session_id)

    # 1. Determine user message
    user_content = ""
    if payload.message:
        user_content = payload.message.strip()
    elif payload.messages and len(payload.messages) > 0:
        user_content = payload.messages[-1].content.strip()

    if not user_content:
        raise HTTPException(status_code=400, detail="Nội dung tin nhắn không được để trống.")

    # 2. Append to session history
    session.add_message("user", user_content)
    messages_history = session.get_messages_dict()

    # 3. Spawn independent async background task feeding the entire conversation into LLM for persona analysis
    background_tasks.add_task(
        style_analyzer.analyze_style_async,
        session.session_id,
        messages_history,
    )

    # 4. Generate response from LLM using the session's detected style
    reply = llm_provider.generate_response(
        messages=messages_history,
        user_style_key=session.user_style,
    )

    # 5. Append assistant reply to session
    session.add_message("assistant", reply)

    active_model = (
        settings.GEMINI_MODEL
        if settings.LLM_PROVIDER == "gemini" and llm_provider.gemini_client
        else settings.GROQ_MODEL if llm_provider.groq_client else "nqk-ai-model"
    )

    return ChatResponsePayload(
        session_id=session.session_id,
        reply=reply,
        user_style=session.user_style,
        style_description=session.style_description,
        model=active_model,
    )


@router.post("/chat/stream")
async def chat_stream_endpoint(payload: ChatRequestPayload, background_tasks: BackgroundTasks):
    session = session_manager.get_or_create_session(payload.session_id)

    user_content = ""
    if payload.message:
        user_content = payload.message.strip()
    elif payload.messages and len(payload.messages) > 0:
        user_content = payload.messages[-1].content.strip()

    if not user_content:
        raise HTTPException(status_code=400, detail="Nội dung tin nhắn không được để trống.")

    session.add_message("user", user_content)
    messages_history = session.get_messages_dict()

    # Spawn independent async background task feeding the entire conversation into LLM for persona analysis
    background_tasks.add_task(
        style_analyzer.analyze_style_async,
        session.session_id,
        messages_history,
    )

    def event_generator():
        import json
        full_response = []
        for chunk in llm_provider.stream_response(messages_history, session.user_style):
            full_response.append(chunk)
            payload = json.dumps({"content": chunk}, ensure_ascii=False)
            yield f"data: {payload}\n\n"
        
        # Save complete assistant reply
        session.add_message("assistant", "".join(full_response))
        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "X-Session-ID": session.session_id,
            "X-User-Style": session.user_style,
        },
    )


@router.get("/session/{session_id}")
def get_session_info(session_id: str):
    if session_id not in session_manager.sessions:
        raise HTTPException(status_code=404, detail="Session không tồn tại hoặc đã hết hạn.")
    session = session_manager.sessions[session_id]
    return {
        "session_id": session.session_id,
        "user_style": session.user_style,
        "style_description": session.style_description,
        "messages": session.get_messages_dict(),
    }
