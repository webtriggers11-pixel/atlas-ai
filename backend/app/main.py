from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.routers.maps import router as maps_router
from app.routers.documents import router as documents_router
from app.routers.gaps import router as gaps_router
from app.api.v1 import api_router
from app.core.security import SecurityHeadersMiddleware, authenticate, llm_limit


def run_migrations():
    """Detect schema changes against live DB and apply any pending migrations."""
    from app.db.base import Base
    import app.models  # noqa: F401 — registers every table in Base.metadata
    from migrations.migration_manager import MigrationManager

    manager = MigrationManager(settings.DATABASE_URL, Base.metadata)
    manager.generate_migration()
    manager.apply_migrations()


def _warmup_ollama():
    """Send a minimal request to Ollama so the model is loaded into RAM before the first real request."""
    import httpx
    try:
        httpx.post(
            f"{settings.OLLAMA_BASE_URL}/api/chat",
            json={
                "model": settings.OLLAMA_MODEL,
                "messages": [{"role": "user", "content": "hi"}],
                "stream": False,
                "keep_alive": -1,
            },
            timeout=120.0,
        )
        print(f"[warmup] {settings.OLLAMA_MODEL} loaded into RAM")
    except Exception as e:
        print(f"[warmup] Ollama not reachable yet: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.AUTO_MIGRATE:
        run_migrations()
    _warmup_ollama()
    yield


app = FastAPI(title="Idea Atlas API", version="0.1.0", lifespan=lifespan)

# Only the configured frontends may call the API from a browser (comma-separated CORS_ORIGINS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()],
    allow_credentials=False,   # tokens travel in the Authorization header, not cookies
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    expose_headers=["Content-Disposition", "Retry-After"],
)
app.add_middleware(SecurityHeadersMiddleware)


# v1 topic explorer: same optional auth; its LLM-backed endpoints share the LLM rate limit
v1_guard = [Depends(authenticate), Depends(llm_limit)]
app.include_router(maps_router, dependencies=v1_guard)
app.include_router(documents_router, dependencies=v1_guard)
app.include_router(gaps_router, dependencies=v1_guard)
app.include_router(api_router)   # V2 gap-analysis API under /api/v1


# GET /health → {"status": "ok", "message": "Idea Atlas backend is running"}
@app.get("/health")
async def health():
    """Return 200 if the backend process is alive."""
    return {"status": "ok", "message": "Idea Atlas backend is running"}


# GET /health/ready
# Example response (200): {"status": "ready", "database": "ok", "pgvector": "0.8.0"}
# Example response (503): {"status": "not_ready", "database": "ok", "pgvector": null}
@app.get("/health/ready")
def health_ready():
    """Return 200 only if Postgres is reachable and the pgvector extension is installed."""
    from sqlalchemy import text
    from app.db import engine

    try:
        with engine.connect() as conn:
            pgvector_version = conn.execute(
                text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
            ).scalar()
    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "database": f"error: {type(exc).__name__}", "pgvector": None},
        )

    body = {"status": "ready" if pgvector_version else "not_ready", "database": "ok", "pgvector": pgvector_version}
    return JSONResponse(status_code=200 if pgvector_version else 503, content=body)
