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
    STRIP_QUERY_BOILERPLATE: bool = False        # search "Apache Kafka" instead of the full sentence — measured: no gain
    REWRITE_BELOW_SCORE: float = 0.5             # only rewrite when the best similarity is below this

    # ── LLM reliability ──
    LLM_MAX_ATTEMPTS: int = 4                 # provider attempts per call (across fallback providers)
    LLM_RETRY_BUDGET_S: float = 20            # max seconds spent waiting on rate limits (interactive requests)
    LLM_BACKGROUND_RETRY_BUDGET_S: float = 150  # same, for background jobs (extraction, analysis)
    LLM_DEFAULT_BACKOFF_S: float = 5          # cooldown when a provider doesn't say how long to wait
    LLM_MAX_BACKOFF_S: float = 60
    CLASSIFY_PROMPT: str = "classify-v2"      # classify-v1 | classify-v2 (kept for evaluation comparisons)

    # ── Gap analysis ──
    EVIDENCE_K: int = 4                 # evidence chunks retrieved per requirement
    ANALYSIS_BATCH_SIZE: int = 4        # requirements classified per LLM call
    MISSING_GUARD_SCORE: float = 0.55   # "missing" with retrieval similarity above this becomes "unclear"

    # ── Security (Phase 12) ──
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_LLM_PER_MINUTE: int = 20        # extract / analyse / chat / investigate, per client
    RATE_LIMIT_UPLOADS_PER_MINUTE: int = 30
    TRUST_PROXY_HEADERS: bool = False          # trust X-Forwarded-For from any peer (only behind your own proxy)
    AUTH_ENABLED: bool = False                 # optional login; off = single-user self-hosted mode
    AUTH_ALLOW_REGISTRATION: bool = True
    JWT_SECRET: str = "change-me"              # required (32+ chars) when AUTH_ENABLED=true
    JWT_EXPIRE_HOURS: int = 24
    LOG_LLM_RAW_OUTPUT: bool = False           # store raw invalid model output (may contain document text)

    # ── Background jobs (Celery + Redis) ──
    CELERY_TASK_ALWAYS_EAGER: bool = False   # true = run tasks inline (tests / no Redis available)

    model_config = {"env_file": Path(__file__).parents[2] / ".env", "extra": "ignore"}


settings = Settings()
