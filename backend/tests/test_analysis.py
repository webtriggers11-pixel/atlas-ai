"""
V2 Phase 5 — gap analysis pipeline: retrieval → classification (LLM mocked) → guardrails → cache.
Run from backend/: pytest tests/test_analysis.py -v
"""
from unittest.mock import patch

import pytest

from app import llm
from app.core.config import settings
from app.services.evidence_verifier import verify_quote

SDD = """## Authentication
Access tokens are signed JWTs that expire after fifteen minutes. Refresh tokens are not described yet.
## Rate Limiting
The gateway allows sixty requests per minute per client and returns HTTP 429 when exceeded.
"""

REQUIREMENTS = [
    "The system must expire access tokens after fifteen minutes.",       # covered (real quote)
    "The system must allow sixty requests per minute per client.",       # model invents a quote → unclear
    "The system must encrypt backups with AES-256.",                     # missing
]


# ── Evidence verifier ─────────────────────────────────────────────────────────

def test_verify_exact_and_normalized_quotes():
    """Exact quotes and quotes differing only in case/curly quotes/punctuation are verified with the SOURCE span."""
    src = "Access tokens are signed JWTs that expire after fifteen minutes. Refresh tokens rotate."
    assert verify_quote("Access tokens are signed JWTs", src).verified
    check = verify_quote("ACCESS TOKENS are signed JWTs that expire after fifteen minutes", src)
    assert check.verified and check.text.startswith("Access tokens")


def test_verify_fuzzy_but_rejects_inventions():
    """A one-word slip passes the 90% fuzzy check; an invented sentence does not."""
    src = "The gateway allows sixty requests per minute per client and returns HTTP 429 when exceeded."
    assert verify_quote("The gateway allows sixty request per minute per client", src).verified
    assert not verify_quote("The gateway allows 100 requests per second", src).verified
    assert not verify_quote("Backups are encrypted with AES-256", src).verified


# ── Pipeline helpers ──────────────────────────────────────────────────────────

def _setup(client) -> str:
    """Project with an indexed existing document and three approved requirements."""
    pid = client.post("/api/v1/projects", json={"name": "Analysis test"}).json()["id"]
    assert client.post(f"/api/v1/projects/{pid}/documents",
                       data={"role": "existing", "title": "sdd", "text": SDD}).status_code == 201
    for text in REQUIREMENTS:
        client.post(f"/api/v1/projects/{pid}/requirements", json={"text": text})
    return pid


def _fake_classify(requirements, excerpts, preset="spec_coverage"):
    """Scripted 'model': real quote for tokens, invented quote for rate limits, missing for backups."""
    results = []
    for r in requirements:
        if "access tokens" in r["text"]:
            ex = next(e for e in excerpts if "fifteen minutes" in e["text"])
            results.append(llm.Classification(id=r["id"], status="covered", confidence=0.9, explanation="Stated in the SDD.",
                                              evidence=[llm.EvidenceQuote(chunk=ex["id"], quote="Access tokens are signed JWTs that expire after fifteen minutes")]))
        elif "sixty requests" in r["text"]:
            results.append(llm.Classification(id=r["id"], status="covered", confidence=0.95, explanation="Rate limit documented.",
                                              evidence=[llm.EvidenceQuote(chunk=excerpts[0]["id"], quote="Clients may send 100 requests per second")]))
        else:
            results.append(llm.Classification(id=r["id"], status="missing", confidence=0.8, explanation="No backup encryption described.",
                                              missing_detail="Backup encryption.", suggested_action="Document backup encryption."))
    return results


def _run(client, pid) -> dict:
    """Start an analysis (runs eagerly in tests) and return the finished run."""
    resp = client.post(f"/api/v1/projects/{pid}/analyze")
    assert resp.status_code == 202, resp.text
    return client.get(f"/api/v1/runs/{resp.json()['id']}").json()


# ── Pipeline ──────────────────────────────────────────────────────────────────

@patch("app.services.analysis_service.llm.classify_requirements", side_effect=_fake_classify)
def test_pipeline_guardrails(mock_llm, client, monkeypatch):
    """Real quotes are stored verified; invented quotes are dropped and the finding is downgraded."""
    monkeypatch.setattr(settings, "MISSING_GUARD_SCORE", 1.01)   # isolate the evidence rule in this test
    pid = _setup(client)
    run = _run(client, pid)
    assert run["status"] == "completed" and run["processed"] == run["total"] == 3

    findings = {f["requirement"]["code"]: f for f in client.get(f"/api/v1/runs/{run['id']}/findings").json()}
    covered, invented, missing = findings["REQ-001"], findings["REQ-002"], findings["REQ-003"]

    assert covered["status"] == "covered" and covered["evidence"][0]["verified"]
    assert covered["evidence"][0]["quote"].startswith("Access tokens are signed JWTs")
    assert covered["evidence"][0]["document_role"] == "existing"

    assert invented["status"] == "unclear" and invented["evidence"] == []
    assert "could not be found" in invented["explanation"]

    assert missing["status"] == "missing" and missing["evidence"] == []
    assert run["stats"]["counts"] == {"covered": 1, "partial": 0, "missing": 1, "conflict": 0, "unclear": 1}
    assert run["stats"]["evidence_dropped"] == 1 and run["stats"]["llm_calls"] == 1


@patch("app.services.analysis_service.llm.classify_requirements", side_effect=_fake_classify)
def test_missing_with_strong_retrieval_match_becomes_unclear(mock_llm, client, monkeypatch):
    """'Missing' needs proof of absence: if retrieval found very similar text, a human must check."""
    monkeypatch.setattr(settings, "MISSING_GUARD_SCORE", -1.0)   # every retrieval score counts as "strong"
    pid = _setup(client)
    run = _run(client, pid)
    backup = next(f for f in client.get(f"/api/v1/runs/{run['id']}/findings").json() if f["requirement"]["code"] == "REQ-003")
    assert backup["status"] == "unclear" and "human should confirm" in backup["explanation"]


@patch("app.services.analysis_service.llm.classify_requirements", side_effect=_fake_classify)
def test_rerun_uses_cache_and_only_reclassifies_changed_requirements(mock_llm, client):
    """Second run with nothing changed → 0 LLM calls; editing one requirement → only it is re-classified."""
    pid = _setup(client)
    first = _run(client, pid)
    second = _run(client, pid)
    assert second["stats"]["cache_hits"] == 3 and second["stats"]["llm_calls"] == 0
    cached = client.get(f"/api/v1/runs/{second['id']}/findings").json()
    assert {f["source"] for f in cached} == {"cache"}
    assert [f["status"] for f in cached] == [f["status"] for f in client.get(f"/api/v1/runs/{first['id']}/findings").json()]

    req = next(r for r in client.get(f"/api/v1/projects/{pid}/requirements").json() if r["code"] == "REQ-003")
    client.patch(f"/api/v1/requirements/{req['id']}", json={"text": "The system must encrypt nightly backups with AES-256."})
    third = _run(client, pid)
    assert third["stats"]["cache_hits"] == 2 and mock_llm.call_count == 2


@patch("app.services.analysis_service.llm.classify_requirements", side_effect=llm.LLMOutputError("garbage"))
def test_llm_failure_degrades_to_failed_run_with_reason(mock_llm, client):
    """If every requirement fails to classify, the run is 'failed' with a readable error (no crash)."""
    pid = _setup(client)
    run = _run(client, pid)
    assert run["status"] == "failed" and "Every requirement failed" in run["error_message"]


def test_partial_llm_failure_still_completes(client):
    """One bad batch → its requirements become 'unclear' with the reason; the rest are analysed."""
    calls = {"n": 0}

    def flaky(requirements, excerpts, preset="spec_coverage"):
        """First batch fails, later batches succeed."""
        calls["n"] += 1
        if calls["n"] == 1:
            raise llm.LLMOutputError("bad json twice")
        return _fake_classify(requirements, excerpts, preset)

    with patch("app.services.analysis_service.llm.classify_requirements", side_effect=flaky), \
         patch.object(settings, "ANALYSIS_BATCH_SIZE", 1):
        pid = _setup(client)
        run = _run(client, pid)
    assert run["status"] == "completed" and run["stats"]["errors"] == 1
    first = next(f for f in client.get(f"/api/v1/runs/{run['id']}/findings").json() if f["requirement"]["code"] == "REQ-001")
    assert first["status"] == "unclear" and "bad json twice" in first["explanation"]


def test_analysis_preconditions(client):
    """No approved requirements → 422; no existing documents → 422."""
    pid = client.post("/api/v1/projects", json={"name": "pre"}).json()["id"]
    assert client.post(f"/api/v1/projects/{pid}/analyze").status_code == 422
    client.post(f"/api/v1/projects/{pid}/requirements", json={"text": "The system must log in users."})
    resp = client.post(f"/api/v1/projects/{pid}/analyze")
    assert resp.status_code == 422 and "existing document" in resp.json()["detail"]


def test_classify_prompt_contains_rules_and_untrusted_note():
    """The classification prompt carries the status definitions, the verbatim-quote rule and the injection guard."""
    captured = {}

    def fake_call(messages, provider, task_type, max_tokens=None, json_mode=False, **kwargs):
        """Capture the prompt and return a valid answer."""
        captured["system"] = messages[0]["content"]
        captured["user"] = messages[1]["content"]
        return '{"results":[{"id":"R1","status":"missing","confidence":0.7,"explanation":"Not mentioned.","evidence":[]}]}'

    with patch("app.llm._call_llm", side_effect=fake_call), patch("app.llm.pick_provider", return_value="groq"):
        out = llm.classify_requirements([{"id": "R1", "text": "Must log errors."}],
                                        [{"id": "C1", "source": "sdd.txt", "text": "Errors go to stdout."}])
    assert out[0].status == "missing"
    assert "WORD FOR WORD" in captured["system"] and "untrusted data" in captured["system"]
    assert "[C1] (sdd.txt) Errors go to stdout." in captured["user"]
