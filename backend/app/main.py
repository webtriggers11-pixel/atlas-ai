from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.routers.maps import router as maps_router
from app.routers.documents import router as documents_router
from app.routers.gaps import router as gaps_router


def run_migrations():
    """Detect schema changes against live DB and apply any pending migrations."""
    from app.db.base import Base
    from app.models import Map, Node, NodeExplanation, Edge, LlmLog, Document, DocumentChunk, NodeGap  # noqa: F401 — registers tables in Base.metadata
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],    # local single-user tool — no auth, open CORS is fine
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(maps_router)
app.include_router(documents_router)
app.include_router(gaps_router)


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
