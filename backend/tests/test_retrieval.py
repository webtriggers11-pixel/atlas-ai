"""
V2 Phase 3 — embeddings stored in pgvector and semantic search in SQL.
Uses the deterministic 'fake' embedder (set in conftest), so results depend on shared words.
Run from backend/: pytest tests/test_retrieval.py -v
"""
from sqlalchemy import text

from app.services.embedding_service import FakeHashProvider, EMBEDDING_DIM

SDD = """## Authentication
Access tokens are signed JWTs that expire after fifteen minutes. The login endpoint returns an access token.
## Rate Limiting
The gateway allows sixty requests per minute per client and returns HTTP 429 when exceeded.
## Audit Logging
Every login attempt is written to the audit log together with the client IP address and a timestamp.
"""

SRS = """## Requirements
The system shall lock an account after five failed password attempts.
"""


def _project_with_docs(client) -> str:
    """Create a project with one existing (SDD) and one reference (SRS) document, both processed."""
    pid = client.post("/api/v1/projects", json={"name": "Retrieval test"}).json()["id"]
    for role, title, body in (("existing", "sdd", SDD), ("reference", "srs", SRS)):
        resp = client.post(f"/api/v1/projects/{pid}/documents", data={"role": role, "title": title, "text": body})
        assert resp.status_code == 201, resp.text
    return pid


def test_fake_embedder_is_normalized_and_deterministic():
    """Vectors are unit length, 384-dim, and identical for identical text."""
    provider = FakeHashProvider()
    a, b = provider.embed(["audit log entry", "audit log entry"])
    assert len(a) == EMBEDDING_DIM and abs(sum(x * x for x in a) - 1.0) < 1e-9
    assert a == b


def test_chunks_get_embeddings_on_ingestion(client, db):
    """Processing stores a 384-dim vector on every chunk."""
    pid = _project_with_docs(client)
    nulls = db.execute(text(
        "SELECT count(*) FROM doc_chunks c JOIN project_documents d ON d.id = c.document_id "
        "WHERE d.project_id = :pid AND c.embedding IS NULL"), {"pid": pid}).scalar()
    dims = db.execute(text(
        "SELECT DISTINCT vector_dims(c.embedding) FROM doc_chunks c JOIN project_documents d ON d.id = c.document_id "
        "WHERE d.project_id = :pid"), {"pid": pid}).scalars().all()
    assert nulls == 0 and dims == [EMBEDDING_DIM]


def test_search_ranks_the_relevant_section_first(client):
    """A query about rate limits returns the Rate Limiting chunk at rank 1 with the best score."""
    pid = _project_with_docs(client)
    results = client.post(f"/api/v1/projects/{pid}/search",
                          json={"query": "how many requests per minute before HTTP 429", "role": "existing", "k": 3}).json()
    assert results[0]["section"] == "Rate Limiting"
    assert results[0]["rank"] == 1
    assert [r["score"] for r in results] == sorted([r["score"] for r in results], reverse=True)


def test_search_filters_by_role_and_project(client):
    """role=reference only searches reference docs; another project's chunks are never returned."""
    pid = _project_with_docs(client)
    other = _project_with_docs(client)

    ref_only = client.post(f"/api/v1/projects/{pid}/search", json={"query": "failed password attempts", "role": "reference"}).json()
    assert ref_only and {r["document_role"] for r in ref_only} == {"reference"}

    all_results = client.post(f"/api/v1/projects/{pid}/search", json={"query": "login", "k": 50}).json()
    other_doc_ids = {d["id"] for d in client.get(f"/api/v1/projects/{other}/documents").json()}
    assert not other_doc_ids & {r["document_id"] for r in all_results}


def test_search_uses_hnsw_index(db, migrated):
    """The HNSW index exists and the planner can use it for an ORDER BY embedding <=> ... LIMIT query."""
    index = db.execute(text(
        "SELECT indexdef FROM pg_indexes WHERE indexname = 'idx_doc_chunks_embedding_hnsw'")).scalar()
    assert "USING hnsw" in index and "vector_cosine_ops" in index

    db.execute(text("SET LOCAL enable_seqscan = off"))   # tiny test tables would otherwise use a seq scan
    vec = "[" + ",".join(["0.05"] * EMBEDDING_DIM) + "]"
    plan = "\n".join(db.execute(text(
        f"EXPLAIN SELECT id FROM doc_chunks ORDER BY embedding <=> '{vec}' LIMIT 5")).scalars().all())
    assert "idx_doc_chunks_embedding_hnsw" in plan


def test_migrator_is_idempotent_with_vector_column(migrated, tmp_path):
    """After migrating, a second diff finds nothing — the vector type round-trips through reflection."""
    import os
    from app.db.base import Base
    from migrations.migration_manager import MigrationManager

    manager = MigrationManager(os.environ["DATABASE_URL"], Base.metadata, migrations_dir=str(tmp_path))
    assert manager.generate_migration() is None


def test_search_validation(client):
    """Blank queries and absurd k values are rejected."""
    pid = client.post("/api/v1/projects", json={"name": "x"}).json()["id"]
    assert client.post(f"/api/v1/projects/{pid}/search", json={"query": "  "}).status_code == 422
    assert client.post(f"/api/v1/projects/{pid}/search", json={"query": "a", "k": 500}).status_code == 422
