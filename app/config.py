import os
from typing import List
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application configuration loaded from environment variables with bulletproof cloud defaults."""

    # LLM Settings
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "groq").lower()
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "").strip()
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash").strip()
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "").strip()
    
    _raw_groq_model = os.getenv("GROQ_MODEL", "").strip()
    GROQ_MODEL: str = _raw_groq_model if (_raw_groq_model and "llama" not in _raw_groq_model and "mixtral" not in _raw_groq_model and "gemma" not in _raw_groq_model) else "openai/gpt-oss-120b"

    # Database Settings (Safe public access only - fallback to Neon production if local dummy credentials on cloud)
    _raw_db_host = os.getenv("DB_HOST", "").strip()
    DB_HOST: str = _raw_db_host if (_raw_db_host and _raw_db_host not in ["localhost", "127.0.0.1", "db"]) else "ep-gentle-dew-axryx2mu-pooler.c-4.us-east-2.aws.neon.tech"
    DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
    _raw_db_name = os.getenv("DB_NAME", "").strip()
    DB_NAME: str = _raw_db_name if (_raw_db_name and _raw_db_name not in ["portfolio", "postgres"]) else "neondb"
    _raw_db_user = os.getenv("DB_USER", "").strip()
    DB_USER: str = _raw_db_user if (_raw_db_user and _raw_db_user not in ["postgres", "root", "admin"]) else "neondb_owner"
    _raw_db_pass = os.getenv("DB_PASSWORD", "").strip()
    DB_PASSWORD: str = _raw_db_pass if (_raw_db_pass and _raw_db_pass not in ["postgres", "admin", "root", "password"]) else "npg_4LRx7pFVeDnr"

    _raw_be_url = os.getenv("PORTFOLIO_BE_URL", "").strip()
    PORTFOLIO_BE_URL: str = _raw_be_url if (_raw_be_url and "localhost" not in _raw_be_url) else "https://nguyenquockhoa.onrender.com/api/v1"
    
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "https://nguyenquockhoaportfolio.vercel.app").rstrip("/")

    # Server Settings
    HOST: str = os.getenv("HOST", "0.0.0.0").strip()
    PORT: int = int(os.getenv("PORT", "8000"))
    CORS_ORIGINS: str = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://localhost:3000,https://nguyenquockhoaportfolio.vercel.app",
    ).strip()

    # Text-to-Speech Settings (Default: "edge-tts" for 100% Free Unlimited Native Vietnamese Voice)
    TTS_PROVIDER: str = os.getenv("TTS_PROVIDER", "edge-tts").lower()
    EDGE_TTS_VOICE: str = os.getenv("EDGE_TTS_VOICE", "vi-VN-HoaiMyNeural").strip()  # vi-VN-HoaiMyNeural (Nữ miền Nam) hoặc vi-VN-NamMinhNeural (Nam miền Nam)
    EDGE_TTS_RATE: str = os.getenv("EDGE_TTS_RATE", "-2%").strip()

    # ElevenLabs Text-to-Speech Settings (Alternative Cloud Provider)
    ELEVENLABS_API_KEY: str = os.getenv("ELEVENLABS_API_KEY", "").strip()
    ELEVENLABS_VOICE_ID: str = os.getenv("ELEVENLABS_VOICE_ID", "x4KAhuXs2G8TfK9Zr7Q4").strip()
    ELEVENLABS_MODEL_ID: str = os.getenv("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2").strip()

    # Session / Cache Settings
    SESSION_TTL_HOURS: int = 24
    KNOWLEDGE_CACHE_TTL_MINUTES: int = 5

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()
