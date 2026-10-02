"""
V2 Phase 4 — requirement extraction job (LLM mocked) and the review flow around it.
Run from backend/: pytest tests/test_extraction.py -v
"""
from unittest.mock import patch

from app import llm
from app.models import DocChunk
from app.services.extraction_job import _strip_overlap, build_batches

SRS = """## 3. Authentication
Users must log in with an email address and a password. Access tokens must expire after 15 minutes.
## 4. Audit
All login attempts must be recorded in an audit log.
"""


def _project_with_reference(client, text=SRS) -> str:
    """Project with one indexed reference document."""
    pid = client.post("/api/v1/projects", json={"name": "Extraction test"}).json()["id"]
    assert client.post(f"/api/v1/projects/{pid}/documents",
                       data={"role": "reference", "title": "srs", "text": text}).status_code == 201
    return pid


def _fake_extract(batch_text, preset="spec_coverage"):
    """Stand-in for the LLM: returns requirements based on which sections are in the batch."""
    reqs = []
    if "Authentication" in batch_text:
        reqs += [
            llm.ExtractedRequirement(text="The system must let users log in with email and password.", section="3. Authentication"),
            llm.ExtractedRequirement(text="The system must expire access tokens after 15 minutes.", section="3. Authentication"),
            # exact duplicate with different spacing/case — must be removed by the hash dedupe
            llm.ExtractedRequirement(text="The system must  expire ACCESS tokens after 15 minutes.", section="3. Authentication"),
        ]
    if "Audit" in batch_text:
        reqs.append(llm.ExtractedRequirement(text="The system must record all login attempts in an audit log.", section="4. Audit"))
    return reqs


def test_strip_overlap_removes_repeated_prefix():
    """The chunk overlap is removed so the LLM doesn't see (and extract) sentences twice."""
    assert _strip_overlap("a b c d e", "d e f g") == "f g"
    assert _strip_overlap("a b c", "x y z") == "x y z"


def test_build_batches_respects_budget_and_tags_sections():
    """Batches stay under the word budget and wrap each chunk in a <section title=...> tag."""
    chunks = [DocChunk(document_id=1, chunk_index=i, content=" ".join([f"w{i}"] * 100), section=f"S{i}", word_count=100)
              for i in range(5)]
    batches = build_batches(chunks, batch_words=250)
    assert [len(b.chunks) for b in batches] == [2, 2, 1]
    assert '<section title="S0">' in batches[0].text


@patch("app.services.extraction_job.llm.extract_requirements", side_effect=_fake_extract)
def test_extraction_creates_deduplicated_drafts_linked_to_sources(mock_llm, client):
    """Extraction → 3 unique drafts with sequential codes, each linked to the chunk it came from."""
    pid = _project_with_reference(client)
    resp = client.post(f"/api/v1/projects/{pid}/requirements/extract")
    assert resp.status_code == 202

    project = client.get(f"/api/v1/projects/{pid}").json()
    assert project["extraction_status"] == "completed" and project["extraction_error"] is None

    drafts = client.get(f"/api/v1/projects/{pid}/requirements?status=draft").json()
    assert [r["code"] for r in drafts] == ["REQ-001", "REQ-002", "REQ-003"]
    assert all(r["origin"] == "extracted" and r["source_chunk_id"] for r in drafts)
    audit = next(r for r in drafts if "audit" in r["text"])
    chunk = next(c for c in client.get(f"/api/v1/documents/{client.get(f'/api/v1/projects/{pid}/documents').json()[0]['id']}/chunks").json()
                 if c["id"] == audit["source_chunk_id"])
    assert chunk["section"] == "4. Audit"


@patch("app.services.extraction_job.llm.extract_requirements", side_effect=_fake_extract)
def test_rerun_keeps_reviewed_requirements(mock_llm, client):
    """Re-extraction replaces unreviewed drafts but keeps approved/manual ones and doesn't duplicate them."""
    pid = _project_with_reference(client)
    client.post(f"/api/v1/projects/{pid}/requirements/extract")
    first = client.get(f"/api/v1/projects/{pid}/requirements").json()
    client.patch(f"/api/v1/requirements/{first[0]['id']}", json={"status": "approved"})
    client.post(f"/api/v1/projects/{pid}/requirements", json={"text": "Passwords must be at least 12 characters."})

    client.post(f"/api/v1/projects/{pid}/requirements/extract")
    after = client.get(f"/api/v1/projects/{pid}/requirements").json()
    texts = [r["text"] for r in after]
    assert len(texts) == len(set(texts)) == 4          # 3 extracted (1 approved kept) + 1 manual
    assert next(r for r in after if r["id"] == first[0]["id"])["status"] == "approved"


@patch("app.services.extraction_job.llm.extract_requirements", side_effect=llm.LLMOutputError("bad json"))
def test_llm_failure_marks_extraction_failed(mock_llm, client):
    """If every batch returns unusable output, the job ends 'failed' with a readable error — no crash."""
    pid = _project_with_reference(client)
    client.post(f"/api/v1/projects/{pid}/requirements/extract")
    project = client.get(f"/api/v1/projects/{pid}").json()
    assert project["extraction_status"] == "failed"
    assert "unusable output" in project["extraction_error"]
    assert client.get(f"/api/v1/projects/{pid}/requirements").json() == []


def test_extraction_preconditions(client):
    """No reference document → 422."""
    pid = client.post("/api/v1/projects", json={"name": "empty"}).json()["id"]
    assert client.post(f"/api/v1/projects/{pid}/requirements/extract").status_code == 422


def test_structured_call_retries_once_with_error_feedback():
    """Bad JSON first, valid JSON second → success; the retry message tells the model what was wrong."""
    calls = []

    def fake_call(messages, provider, task_type, max_tokens=None, json_mode=False, **kwargs):
        """First reply is invalid; second is valid."""
        calls.append(messages)
        return "not json" if len(calls) == 1 else '{"requirements":[{"text":"The system must log errors.","section":null}]}'

    with patch("app.llm._call_llm", side_effect=fake_call), patch("app.llm.pick_provider", return_value="groq"):
        result = llm.extract_requirements("<section>Errors must be logged.</section>")
    assert result[0].text == "The system must log errors."
    assert len(calls) == 2 and "invalid" in calls[1][-1]["content"]
    assert "untrusted data" in calls[0][0]["content"]          # prompt-injection guard is in the system prompt


def test_structured_call_raises_after_two_failures():
    """Two invalid replies → LLMOutputError (callers degrade gracefully instead of crashing)."""
    import pytest

    with patch("app.llm._call_llm", return_value='{"wrong": 1}'), patch("app.llm.pick_provider", return_value="groq"):
        with pytest.raises(llm.LLMOutputError):
            llm.extract_requirements("<section>x</section>")
