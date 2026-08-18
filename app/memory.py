import time
import uuid
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class ChatTurn(BaseModel):
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: float = Field(default_factory=time.time)


class ConversationSession(BaseModel):
    session_id: str
    messages: List[ChatTurn] = Field(default_factory=list)
    user_style: str = "trung_tinh"  # Detected user personality/style
    style_description: str = "Tự nhiên, thân thiện và chuyên nghiệp"
    last_activity: float = Field(default_factory=time.time)

    def add_message(self, role: str, content: str):
        self.messages.append(ChatTurn(role=role, content=content))
        self.last_activity = time.time()
        # Keep last 20 messages for context efficiency
        if len(self.messages) > 20:
            self.messages = self.messages[-20:]

    def get_messages_dict(self) -> List[Dict[str, str]]:
        return [{"role": m.role, "content": m.content} for m in self.messages]


class SessionManager:
    def __init__(self, ttl_hours: int = 24):
        self.sessions: Dict[str, ConversationSession] = {}
        self.ttl_seconds = ttl_hours * 3600

    def get_or_create_session(self, session_id: Optional[str] = None) -> ConversationSession:
        self._cleanup_expired_sessions()

        if not session_id or session_id not in self.sessions:
            new_id = session_id or str(uuid.uuid4())
            self.sessions[new_id] = ConversationSession(session_id=new_id)
            return self.sessions[new_id]

        session = self.sessions[session_id]
        session.last_activity = time.time()
        return session

    def update_user_style(self, session_id: str, style_key: str, style_desc: str):
        if session_id in self.sessions:
            self.sessions[session_id].user_style = style_key
            self.sessions[session_id].style_description = style_desc

    def _cleanup_expired_sessions(self):
        now = time.time()
        expired = [
            sid
            for sid, s in self.sessions.items()
            if (now - s.last_activity) > self.ttl_seconds
        ]
        for sid in expired:
            del self.sessions[sid]


# Global session manager instance
session_manager = SessionManager()
