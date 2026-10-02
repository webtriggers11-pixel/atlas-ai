"""
V2 Phase 1 — projects, documents, requirements, runs/findings API against the test database.
Run from backend/: pytest tests/test_projects_api.py -v
"""
import hashlib
from uuid import uuid4

from app.models import ProjectDocument, DocChunk, AnalysisRun, Finding, Evidence, Requirement


def _project(client, name="Payments API review", preset="spec_coverage") -> dict:
    """Create a project through the API and return its JSON."""
    resp = client.post("/api/v1/projects", json={"name": name, "preset": preset})
    assert resp.status_code == 201, resp.text
    return resp.json()


def _document(db, project_id, role="reference", filename="srs.txt") -> ProjectDocument:
    """Insert a document row directly (upload itself is covered by the ingestion tests)."""
    doc = ProjectDocument(
        project_id=project_id, role=role, filename=filename, file_type="txt", size_bytes=10,
        content_hash=hashlib.sha256(uuid4().bytes).hexdigest(), storage_path=f"{project_id}/{uuid4()}.txt",
    )
    db.add(doc)
    db.flush()
    return doc


# ── Projects ──────────────────────────────────────────────────────────────────

def test_create_and_get_project(client):
    """Created project comes back with zero counts and is retrievable by id."""
    project = _project(client)
    assert project["preset"] == "spec_coverage"
    assert project["reference_documents"] == 0 and project["requirements"] == 0

    resp = client.get(f"/api/v1/projects/{project['id']}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Payments API review"


def test_project_validation(client):
    """Blank names and unknown presets are rejected with 422."""
    assert client.post("/api/v1/projects", json={"name": "   "}).status_code == 422
    assert client.post("/api/v1/projects", json={"name": "x", "preset": "nope"}).status_code == 422


def test_list_rename_delete_project(client):
    """A project can be listed, renamed and deleted; afterwards it is 404."""
    project = _project(client)
    assert any(p["id"] == project["id"] for p in client.get("/api/v1/projects").json())

    resp = client.patch(f"/api/v1/projects/{project['id']}", json={"name": "Renamed"})
    assert resp.status_code == 200 and resp.json()["name"] == "Renamed"

    assert client.delete(f"/api/v1/projects/{project['id']}").status_code == 204
    assert client.get(f"/api/v1/projects/{project['id']}").status_code == 404


def test_unknown_project_is_404(client):
    """Every project-scoped route returns 404 for an unknown id."""
    missing = uuid4()
    assert client.get(f"/api/v1/projects/{missing}").status_code == 404
    assert client.get(f"/api/v1/projects/{missing}/documents").status_code == 404
    assert client.get(f"/api/v1/projects/{missing}/requirements").status_code == 404


# ── Documents ─────────────────────────────────────────────────────────────────

def test_documents_listed_by_role_and_counted(client, db):
    """Documents are filterable by role and counted on the project."""
    project = _project(client)
    _document(db, project["id"], "reference", "srs.txt")
    _document(db, project["id"], "existing", "sdd.txt")
    _document(db, project["id"], "existing", "api.txt")

    refs = client.get(f"/api/v1/projects/{project['id']}/documents?role=reference").json()
    assert [d["filename"] for d in refs] == ["srs.txt"]

    counts = client.get(f"/api/v1/projects/{project['id']}").json()
    assert counts["reference_documents"] == 1 and counts["existing_documents"] == 2


def test_delete_document_cascades_chunks(client, db):
    """Deleting a document removes its chunks through the database FK cascade."""
    project = _project(client)
    doc = _document(db, project["id"])
    db.add(DocChunk(document_id=doc.id, chunk_index=0, content="hello", word_count=1))
    db.flush()

    assert client.get(f"/api/v1/documents/{doc.id}/chunks").json()[0]["content"] == "hello"
    assert client.delete(f"/api/v1/documents/{doc.id}").status_code == 204
    db.expire_all()
    assert db.query(DocChunk).filter_by(document_id=doc.id).count() == 0


def test_duplicate_document_hash_rejected_by_db(client, db):
    """The (project_id, content_hash) unique index stops the same file being stored twice."""
    import pytest
    from sqlalchemy.exc import IntegrityError

    project = _project(client)
    doc = _document(db, project["id"])
    db.add(ProjectDocument(
        project_id=doc.project_id, role="existing", filename="copy.txt", file_type="txt", size_bytes=10,
        content_hash=doc.content_hash, storage_path="x/y.txt",
    ))
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


# ── Requirements ──────────────────────────────────────────────────────────────

def test_manual_requirements_get_sequential_codes(client):
    """Manually added requirements get REQ-001, REQ-002 ... and start approved."""
    project = _project(client)
    url = f"/api/v1/projects/{project['id']}/requirements"
    first = client.post(url, json={"text": "Users can reset their password.", "section": "Auth"}).json()
    second = client.post(url, json={"text": "Passwords are hashed with bcrypt."}).json()
    assert (first["code"], second["code"]) == ("REQ-001", "REQ-002")
    assert first["status"] == "approved" and first["origin"] == "manual"


def test_review_flow_edit_reject_approve_all_merge(client, db):
    """Edit text, reject one, approve all drafts, merge two — the human review step."""
    project = _project(client)
    pid = project["id"]
    reqs = []
    for i, text in enumerate(["Token expiry 15 min", "Refresh tokens", "Refresh token rotation", "Audit log"], start=1):
        r = Requirement(project_id=pid, code=f"REQ-{i:03d}", text=text, content_hash=str(i))
        db.add(r)
        reqs.append(r)
    db.flush()

    edited = client.patch(f"/api/v1/requirements/{reqs[0].id}", json={"text": "Access tokens expire after 15 minutes."})
    assert edited.json()["text"] == "Access tokens expire after 15 minutes."

    client.patch(f"/api/v1/requirements/{reqs[3].id}", json={"status": "rejected"})
    assert client.post(f"/api/v1/projects/{pid}/requirements/approve-all").json() == {"approved": 3}

    merged = client.post(f"/api/v1/projects/{pid}/requirements/merge",
                         json={"ids": [str(reqs[1].id), str(reqs[2].id)]}).json()
    assert merged["code"] == "REQ-002" and merged["text"] == "Refresh tokens Refresh token rotation"

    statuses = {r["code"]: r["status"] for r in client.get(f"/api/v1/projects/{pid}/requirements").json()}
    assert statuses == {"REQ-001": "approved", "REQ-002": "approved", "REQ-003": "rejected", "REQ-004": "rejected"}

    counts = client.get(f"/api/v1/projects/{pid}").json()
    assert counts["requirements"] == 2 and counts["approved_requirements"] == 2


# ── Runs & findings ───────────────────────────────────────────────────────────

def test_findings_with_evidence(client, db):
    """A run's findings come back with requirement info and evidence citing the source document."""
    project = _project(client)
    doc = _document(db, project["id"], "existing", "sdd.txt")
    chunk = DocChunk(document_id=doc.id, chunk_index=0, content="Access tokens are JWTs valid for 15 minutes.",
                     section="4. Auth", page_start=3, word_count=8)
    req = Requirement(project_id=project["id"], code="REQ-001", text="Access tokens expire after 15 minutes.",
                      content_hash="h", status="approved")
    run = AnalysisRun(project_id=project["id"], status="completed", total=1, processed=1)
    db.add_all([chunk, req, run])
    db.flush()
    finding = Finding(run_id=run.id, requirement_id=req.id, status="covered", confidence=0.9,
                      explanation="The SDD states a 15 minute lifetime.")
    db.add(finding)
    db.flush()
    db.add(Evidence(finding_id=finding.id, chunk_id=chunk.id, quote="JWTs valid for 15 minutes", verified=True, score=0.82))
    db.flush()

    runs = client.get(f"/api/v1/projects/{project['id']}/runs").json()
    assert runs[0]["status"] == "completed"

    findings = client.get(f"/api/v1/runs/{run.id}/findings").json()
    assert len(findings) == 1
    ev = findings[0]["evidence"][0]
    assert findings[0]["requirement"]["code"] == "REQ-001"
    assert (ev["document_filename"], ev["document_role"], ev["page_start"], ev["verified"]) == ("sdd.txt", "existing", 3, True)

    assert client.get(f"/api/v1/runs/{run.id}/findings?status=missing").json() == []
    assert client.get(f"/api/v1/findings/{finding.id}").json()["status"] == "covered"
    assert client.get(f"/api/v1/projects/{project['id']}").json()["latest_run_status"] == "completed"


# ── UI support endpoints ──────────────────────────────────────────────────────

def test_project_summary_has_latest_completed_counts(client, db):
    """finding_counts/last_analyzed_at come from the latest COMPLETED run (a newer failed run is ignored)."""
    project = _project(client)
    assert client.get(f"/api/v1/projects/{project['id']}").json()["finding_counts"] is None
    done = AnalysisRun(project_id=project["id"], status="completed", stats={"counts": {"covered": 3, "missing": 1}})
    db.add(done)
    db.flush()
    db.add(AnalysisRun(project_id=project["id"], status="failed"))
    db.flush()
    body = client.get(f"/api/v1/projects/{project['id']}").json()
    assert body["finding_counts"] == {"covered": 3, "missing": 1}


def test_global_documents_list_with_project_name_and_search(client, db):
    """GET /documents lists documents across projects with their project name; search filters by filename."""
    p1, p2 = _project(client, name="Alpha"), _project(client, name="Beta")
    _document(db, p1["id"], filename="alpha-spec.txt")
    _document(db, p2["id"], filename="beta-resume.txt")
    names = {d["filename"]: d["project_name"] for d in client.get("/api/v1/documents").json()}
    assert names["alpha-spec.txt"] == "Alpha" and names["beta-resume.txt"] == "Beta"
    found = client.get("/api/v1/documents?search=resume").json()
    assert [d["filename"] for d in found if d["filename"].endswith(".txt") and "resume" in d["filename"]] == ["beta-resume.txt"]


def test_finding_includes_requirement_source_document(client, db):
    """Findings carry the reference document the requirement came from (for conflict cards)."""
    project = _project(client)
    ref = _document(db, project["id"], "reference", "srs.txt")
    ref_chunk = DocChunk(document_id=ref.id, chunk_index=0, content="Tokens expire after 15 minutes.", page_start=2, word_count=5)
    db.add(ref_chunk)
    db.flush()
    req = Requirement(project_id=project["id"], code="REQ-001", text="Tokens expire after 15 minutes.",
                      content_hash="h", status="approved", source_chunk_id=ref_chunk.id)
    run = AnalysisRun(project_id=project["id"], status="completed")
    db.add_all([req, run])
    db.flush()
    db.add(Finding(run_id=run.id, requirement_id=req.id, status="missing", explanation="Not mentioned."))
    db.flush()
    finding = client.get(f"/api/v1/runs/{run.id}/findings").json()[0]
    assert (finding["requirement"]["source_document"], finding["requirement"]["source_page"]) == ("srs.txt", 2)


def test_settings_endpoint_never_returns_keys(client):
    """Settings exposes providers/models/limits but no secret values."""
    from app.core.config import settings as cfg

    body = client.get("/api/v1/settings").json()
    assert {p["name"] for p in body["providers"]} == {"groq", "gemini", "ollama"}
    raw = str(body)
    for secret in (cfg.GROQ_API_KEY, cfg.GEMINI_API_KEY):
        assert not secret or secret not in raw
