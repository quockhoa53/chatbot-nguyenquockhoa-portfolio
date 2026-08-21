import asyncio
import hashlib
import io
import logging
import re
from typing import List, Optional
import httpx
from fastapi import APIRouter, BackgroundTasks, HTTPException, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.config import settings
from app.database import fetch_conversations_from_db, get_live_portfolio_data, save_conversation_to_db
from app.llm_provider import llm_provider
from app.memory import session_manager
from app.style_analyzer import STYLE_PROMPT_DIRECTIVES, style_analyzer

logger = logging.getLogger("routes")
router = APIRouter(prefix="/api")

# In-memory audio cache to save API quota (MD5 -> bytes)
_audio_cache = {}


class IncomingChatMessage(BaseModel):
    role: str  # 'user' or 'assistant'
    content: str


class ChatRequestPayload(BaseModel):
    session_id: str
    message: Optional[str] = None
    messages: Optional[List[IncomingChatMessage]] = None


class ChatResponsePayload(BaseModel):
    session_id: str
    reply: str
    user_style: str
    style_description: str
    model: str


class TTSRequestPayload(BaseModel):
    text: str
    voice_id: Optional[str] = None


def clean_text_for_tts(raw_text: str) -> str:
    """Prepares text for natural speech synthesis by removing code blocks, links, thinking tags, and action payloads."""
    if not raw_text:
        return ""
    text = re.sub(r"<think>[\s\S]*?</think>", "", raw_text, flags=re.IGNORECASE)
    text = re.sub(r"```[\s\S]*?```", "", text)
    text = re.sub(r"`[^`]+`", "", text)
    text = re.sub(r"\[ACTION_CONFIRM_CONTACT:[\s\S]*?\]", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"[*_#~>`]", "", text)
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


@router.post("/tts")
async def text_to_speech_endpoint(payload: TTSRequestPayload):
    """Multi-provider Neural TTS: Microsoft Edge TTS (100% Free & Unlimited) + ElevenLabs + In-Memory Cache."""
    clean_text = clean_text_for_tts(payload.text)
    if not clean_text:
        raise HTTPException(status_code=400, detail="Văn bản cần đọc không hợp lệ.")

    # Limit text length per request to 500 characters
    if len(clean_text) > 500:
        clean_text = clean_text[:497] + "..."

    # Check cache first
    voice_identifier = payload.voice_id or (settings.EDGE_TTS_VOICE if settings.TTS_PROVIDER == "edge-tts" else settings.ELEVENLABS_VOICE_ID)
    cache_key = hashlib.md5(f"{clean_text}_{voice_identifier}".encode("utf-8")).hexdigest()
    if cache_key in _audio_cache:
        logger.info(f"🔊 [TTS Cache Hit] Returning cached audio for '{clean_text[:30]}...'")
        return Response(content=_audio_cache[cache_key], media_type="audio/mpeg")

    # 1. Primary Provider: Microsoft Edge Neural TTS (100% Free Native Vietnamese: Hoai My / Nam Minh)
    if settings.TTS_PROVIDER == "edge-tts":
        try:
            import edge_tts
            voice = payload.voice_id if (payload.voice_id and "vi-VN" in payload.voice_id) else settings.EDGE_TTS_VOICE
            communicate = edge_tts.Communicate(clean_text, voice=voice, rate=settings.EDGE_TTS_RATE)
            fp = io.BytesIO()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    fp.write(chunk["data"])
            audio_bytes = fp.getvalue()

            if audio_bytes and len(audio_bytes) > 500:
                if len(_audio_cache) > 100:
                    _audio_cache.pop(next(iter(_audio_cache)))
                _audio_cache[cache_key] = audio_bytes
                logger.info(f"🔊 [Edge-TTS Success ({voice})] Generated {len(audio_bytes)} bytes audio for '{clean_text[:30]}...'")
                return Response(content=audio_bytes, media_type="audio/mpeg")
        except Exception as e:
            logger.warning(f"Edge-TTS generation failed, attempting ElevenLabs/Browser fallback: {e}")

    # 2. Secondary Provider: ElevenLabs
    if settings.ELEVENLABS_API_KEY:
        voice_id = payload.voice_id or settings.ELEVENLABS_VOICE_ID
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

        headers = {
            "xi-api-key": settings.ELEVENLABS_API_KEY,
            "Content-Type": "application/json",
        }

        body = {
            "text": clean_text,
            "model_id": settings.ELEVENLABS_MODEL_ID,
            "voice_settings": {
                "stability": 0.32,
                "similarity_boost": 0.82,
                "style": 0.45,
                "use_speaker_boost": True,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(url, json=body, headers=headers)
                
                # If library voice requires paid subscription (400 or 402), fallback to best pre-made female voice
                if resp.status_code in [400, 402] and voice_id not in ["cgSgspJ2msm6clMCkdW9", "EXAVITQu4vr4xnSDxMaL"]:
                    fallback_voice = "cgSgspJ2msm6clMCkdW9"  # Jessica
                    fallback_url = f"https://api.elevenlabs.io/v1/text-to-speech/{fallback_voice}"
                    resp = await client.post(fallback_url, json=body, headers=headers)

                if resp.status_code == 200:
                    audio_bytes = resp.content
                    if len(_audio_cache) > 100:
                        _audio_cache.pop(next(iter(_audio_cache)))
                    _audio_cache[cache_key] = audio_bytes
                    logger.info(f"🔊 [ElevenLabs Success] Generated {len(audio_bytes)} bytes audio for '{clean_text[:30]}...'")
                    return Response(content=audio_bytes, media_type="audio/mpeg")
        except Exception as e:
            logger.error(f"ElevenLabs request error: {e}")

    # 3. Fallback: Browser Web Speech API
    raise HTTPException(status_code=503, detail="FALLBACK_BROWSER_TTS")


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

    # 6. Asynchronously persist conversation to PostgreSQL as JSONB
    background_tasks.add_task(
        save_conversation_to_db,
        session.session_id,
        session.user_style,
        session.style_description,
        session.get_messages_dict(),
    )

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
        full_reply = "".join(full_response)
        session.add_message("assistant", full_reply)

        # Asynchronously persist conversation to PostgreSQL as JSONB via dedicated daemon thread
        try:
            import threading
            threading.Thread(
                target=save_conversation_to_db,
                args=(
                    session.session_id,
                    session.user_style,
                    session.style_description,
                    session.get_messages_dict(),
                ),
                daemon=True,
            ).start()
        except Exception as e:
            logger.error(f"Error spawning conversation saver thread: {e}")

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


@router.get("/conversations")
def get_stored_conversations(limit: int = 50, offset: int = 0):
    """Admin / Data collection endpoint retrieving stored conversations from PostgreSQL."""
    return {
        "data": fetch_conversations_from_db(limit=limit, offset=offset)
    }

