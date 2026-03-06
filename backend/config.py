# config.py
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # ── Application ──────────────────────────────────────────
    APP_ENV: str = "development"
    SECRET_KEY: str = "your-256-bit-secret-key-here"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── Database ─────────────────────────────────────────────
    DATABASE_URL: str = "sqlite+aiosqlite:///./timetable_dev.db"

    # ── Redis ────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_PUBSUB_CHANNEL: str = "scheduling_events"

    # ── Ollama / LLM ────────────────────────────────────────
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    PRIMARY_MODEL: str = "qwen2.5:14b"
    FALLBACK_MODEL: str = "phi4:14b"
    EMBEDDING_MODEL: str = "nomic-embed-text"
    LLM_TIMEOUT_SECONDS: int = 90
    LLM_MAX_RETRIES: int = 2

    # ── ChromaDB ─────────────────────────────────────────────
    CHROMA_PERSIST_DIR: str = "./chroma_data"
    CHROMA_COLLECTION_NAME: str = "faculty_preferences"

    # ── Solver ───────────────────────────────────────────────
    SOLVER_TIME_LIMIT_SECONDS: int = 120
    SOLVER_NUM_WORKERS: int = 8

    # ── Notifications ────────────────────────────────────────
    WHATSAPP_API_URL: str = "https://graph.facebook.com/v18.0"
    WHATSAPP_PHONE_NUMBER_ID: str = "your-phone-number-id"
    WHATSAPP_ACCESS_TOKEN: str = "your-access-token"
    WHATSAPP_WEBHOOK_VERIFY_TOKEN: str = "your-webhook-verify-token"

    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 25
    SMTP_FROM_EMAIL: str = "timetable@yourcollege.edu"
    SMTP_FROM_NAME: str = "Timetable System"
    SMTP_TLS: bool = False

    SUBSTITUTION_TIMEOUT_MINUTES: int = 10
    SUBSTITUTION_MAX_ESCALATIONS: int = 3

    # ── NVIDIA NIM (Kimi K2.5) ──────────────────────────────
    NVIDIA_API_KEY: str = ""
    NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"
    NVIDIA_MODEL: str = "moonshotai/kimi-k2-instruct"

    # ── WeasyPrint ───────────────────────────────────────────
    PDF_OUTPUT_DIR: str = "./generated_pdfs"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore",
    }


settings = Settings()
