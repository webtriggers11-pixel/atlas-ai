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

    # ── Embeddings + retrieval ──
    EMBEDDING_PROVIDER: str = "local"            # local (MiniLM on CPU) | fake (tests)
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    HNSW_EF_SEARCH: int = 100                    # candidates HNSW examines per query (recall vs speed)
    # Defaults chosen by evaluation (idea-atlas-docs/v2/EVAL_RESULTS.md): on our labelled set hybrid and
    # query rewriting did NOT beat plain vector search, so they are available but off by default.
    RETRIEVAL_MODE: str = "vector"               # vector | hybrid (vector + full-text, fused with RRF)
    RRF_K: int = 60                              # Reciprocal Rank Fusion constant (standard value)
    HYBRID_CANDIDATES: int = 20                  # candidates taken from each ranking before fusion
    QUERY_REWRITE: bool = False                  # LLM rephrasings for weak matches (hybrid mode only)
    REWRITE_BELOW_SCORE: float = 0.5             # only rewrite when the best similarity is below this

    # ── Gap analysis ──
    EVIDENCE_K: int = 4                 # evidence chunks retrieved per requirement
    ANALYSIS_BATCH_SIZE: int = 4        # requirements classified per LLM call
    MISSING_GUARD_SCORE: float = 0.55   # "missing" with retrieval similarity above this becomes "unclear"

    # ── Background jobs (Celery + Redis) ──
    CELERY_TASK_ALWAYS_EAGER: bool = False   # true = run tasks inline (tests / no Redis available)

    model_config = {"env_file": Path(__file__).parents[2] / ".env", "extra": "ignore"}


settings = Settings()
