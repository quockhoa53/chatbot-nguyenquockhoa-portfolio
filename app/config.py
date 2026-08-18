import os
from typing import List
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application configuration loaded from environment variables."""

    # LLM Settings
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "gemini").lower()
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "").strip()
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash").strip()
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "").strip()
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b").strip()

    # Database Settings (Safe public access only)
    DB_HOST: str = os.getenv("DB_HOST", "ep-gentle-dew-axryx2mu-pooler.c-4.us-east-2.aws.neon.tech").strip()
    DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
    DB_NAME: str = os.getenv("DB_NAME", "neondb").strip()
    DB_USER: str = os.getenv("DB_USER", "neondb_owner").strip()
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "npg_4LRx7pFVeDnr").strip()
    PORTFOLIO_BE_URL: str = os.getenv(
        "PORTFOLIO_BE_URL", "https://nguyenquockhoa.onrender.com/api/v1"
    ).strip()

    # Server Settings
    HOST: str = os.getenv("HOST", "0.0.0.0").strip()
    PORT: int = int(os.getenv("PORT", "8000"))
    CORS_ORIGINS: str = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://localhost:3000,https://nguyenquockhoaportfolio.vercel.app",
    ).strip()

    # Session / Cache Settings
    SESSION_TTL_HOURS: int = 24
    KNOWLEDGE_CACHE_TTL_MINUTES: int = 5

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()
