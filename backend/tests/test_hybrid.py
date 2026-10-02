"""
V2 Phase 7 — keyword search, hybrid (RRF) fusion and query rewriting for weak matches.
Run from backend/: pytest tests/test_hybrid.py -v
"""
from unittest.mock import patch

from sqlalchemy import text

from app.core.config import settings
from app.models import Requirement
from app.services import analysis_service, retrieval

DOC = """## Errors
Errors are returned as JSON with a code field such as PF-1042 and a message.
## Tokens
Access tokens are valid for 900 seconds.
## Webhooks
Failed webhook deliveries are retried three times.
"""


def _project(client) -> str:
    """Project with one indexed existing document."""
    pid = client.post("/api/v1/projects", json={"name": "Hybrid test"}).json()["id"]
    client.post(f"/api/v1/projects/{pid}/documents", data={"role": "existing", "title": "sdd", "text": DOC})
    return pid


def test_tsvector_column_is_generated_and_indexed(client, db):
    """Postgres fills tsv automatically (generated column) and a GIN index exists."""
    pid = _project(client)
    filled = db.execute(text(
        "SELECT count(*) FROM doc_chunks c JOIN project_documents d ON d.id = c.document_id "
        "WHERE d.project_id = :pid AND c.tsv IS NOT NULL"), {"pid": pid}).scalar()
    assert filled >= 3
    index = db.execute(text("SELECT indexdef FROM pg_indexes WHERE indexname = 'idx_doc_chunks_tsv_gin'")).scalar()
    assert "USING gin" in index


def test_keyword_search_finds_exact_identifier(client, db):
    """An identifier like PF-1042 is found by full-text search; OR semantics tolerate extra words."""
    pid = _project(client)
    rows = retrieval.keyword_search(pid, "every error response must include the code PF-1042", db, role="existing")
    assert rows and rows[0][0].section == "Errors"


def test_hybrid_fuses_and_keeps_cosine_scale(client, db):
    """Hybrid returns RRF-ordered chunks; `score` is still a cosine similarity, `fused` the RRF score."""
    pid = _project(client)
    hits = retrieval.hybrid_search(pid, ["error code PF-1042"], db, role="existing", k=3)
    assert hits[0].chunk.section == "Errors"
    assert [h.fused for h in hits] == sorted([h.fused for h in hits], reverse=True)
    assert all(-1.0 <= h.score <= 1.0 for h in hits)


def test_extra_phrasings_change_the_ranking(client, db):
    """An alternative phrasing (unit conversion) pulls the right chunk to the top."""
    pid = _project(client)
    base = retrieval.hybrid_search(pid, ["tokens expire after 15 minutes"], db, role="existing", k=3)
    rewritten = retrieval.hybrid_search(pid, ["tokens expire after 15 minutes", "valid for 900 seconds"], db,
                                        role="existing", k=3)
    assert rewritten[0].chunk.section == "Tokens"
    assert rewritten[0].fused >= base[0].fused


def test_rewriting_only_for_weak_matches(client, db, monkeypatch):
    """Only requirements whose best similarity is below REWRITE_BELOW_SCORE are sent for rewriting, in one batch."""
    monkeypatch.setattr(settings, "RETRIEVAL_MODE", "hybrid")
    monkeypatch.setattr(settings, "QUERY_REWRITE", True)
    pid = _project(client)
    strong = Requirement(project_id=pid, code="REQ-001", text="Errors are returned as JSON with a code field such as PF-1042",
                         content_hash="a", status="approved")
    weak = Requirement(project_id=pid, code="REQ-002", text="Bachelor degree holders only", content_hash="b", status="approved")
    db.add_all([strong, weak])
    db.flush()
    monkeypatch.setattr(settings, "REWRITE_BELOW_SCORE", 0.6)

    with patch("app.services.analysis_service.llm.rewrite_queries", return_value={"R1": ["B.E. degree"]}) as rewrite:
        stats = {}
        analysis_service.retrieve_for_requirements(pid, [strong, weak], db, stats)
    sent = [r["text"] for r in rewrite.call_args.args[0]]
    assert sent == ["Bachelor degree holders only"]
    assert stats == {"rewrite_calls": 1, "rewritten": 1}


def test_vector_mode_skips_rewriting(client, db, monkeypatch):
    """With RETRIEVAL_MODE=vector the baseline behaviour is unchanged: no rewriting calls."""
    monkeypatch.setattr(settings, "RETRIEVAL_MODE", "vector")
    pid = _project(client)
    req = Requirement(project_id=pid, code="REQ-001", text="unrelated words", content_hash="c", status="approved")
    db.add(req)
    db.flush()
    with patch("app.services.analysis_service.llm.rewrite_queries") as rewrite:
        analysis_service.retrieve_for_requirements(pid, [req], db, {})
    rewrite.assert_not_called()


def test_search_api_mode_switch(client):
    """The search endpoint accepts mode=vector|hybrid and rejects unknown modes."""
    pid = _project(client)
    for mode in ("vector", "hybrid"):
        resp = client.post(f"/api/v1/projects/{pid}/search", json={"query": "PF-1042 error code", "mode": mode})
        assert resp.status_code == 200 and resp.json()[0]["section"] == "Errors"
    assert client.post(f"/api/v1/projects/{pid}/search", json={"query": "x", "mode": "magic"}).status_code == 422
