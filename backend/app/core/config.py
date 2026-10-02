from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    """Reads all values from the .env file in the backend directory."""

    DATABASE_URL: str
    REDIS_URL: str = "redis://localhost:6379"
    LLM_PROVIDER: str = "ollama"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.1:8b"
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama3-8b-8192"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"
    CORS_ORIGINS: str = "http://localhost:5173"
    PORT: int = 8000
    AUTO_MIGRATE: bool = False
    GAP_THRESHOLD: float = 0.35  # best chunk similarity below this = node is under-documented
    UPLOAD_DIR: str = "uploads"   # where uploaded project documents are stored (relative to backend/)

    # ── V2 ingestion ──
    MAX_UPLOAD_MB: int = 20
    MAX_PDF_PAGES: int = 500
    CHUNK_WORDS: int = 180          # MiniLM reads at most 256 tokens (~190 words); longer chunks get truncated
    CHUNK_OVERLAP_WORDS: int = 30

    # ── Background jobs (Celery + Redis) ──
    CELERY_TASK_ALWAYS_EAGER: bool = False   # true = run tasks inline (tests / no Redis available)

    model_config = {"env_file": Path(__file__).parents[2] / ".env", "extra": "ignore"}


settings = Settings()
