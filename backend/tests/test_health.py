"""
Health endpoint tests — the database engine is mocked, so no Postgres is needed.
Run from backend/: pytest tests/test_health.py -v
"""
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.main import app

client = TestClient(app)  # not used as a context manager → startup hooks (migrations, Ollama warmup) do not run


def _engine_returning(pgvector_version):
    """Build a fake SQLAlchemy engine whose query returns the given pgvector version."""
    engine = MagicMock()
    conn = engine.connect.return_value.__enter__.return_value
    conn.execute.return_value.scalar.return_value = pgvector_version
    return engine


def test_health_liveness():
    """GET /health returns 200 without touching the database."""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_ready_when_pgvector_installed():
    """GET /health/ready returns 200 with the extension version when pgvector is installed."""
    with patch("app.db.engine", _engine_returning("0.8.0")):
        resp = client.get("/health/ready")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ready", "database": "ok", "pgvector": "0.8.0"}


def test_not_ready_when_pgvector_missing():
    """GET /health/ready returns 503 when the database is up but pgvector is not installed."""
    with patch("app.db.engine", _engine_returning(None)):
        resp = client.get("/health/ready")
    assert resp.status_code == 503
    assert resp.json()["pgvector"] is None


def test_not_ready_when_database_down():
    """GET /health/ready returns 503 when Postgres cannot be reached."""
    engine = MagicMock()
    engine.connect.side_effect = OperationalError("SELECT 1", {}, Exception("connection refused"))
    with patch("app.db.engine", engine):
        resp = client.get("/health/ready")
    assert resp.status_code == 503
    assert resp.json()["database"] == "error: OperationalError"
