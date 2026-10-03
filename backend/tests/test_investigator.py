"""
V2 Phase 10 — investigator agent: verdict guardrails, outcomes, traces, scoping. Model is scripted.
Run from backend/: pytest tests/test_investigator.py -v
"""
from unittest.mock import patch

from app import llm
from app.models import AnalysisRun, Finding, Requirement

SDD = """## Authentication
Access tokens are valid for 900 seconds after which the API returns 401.
## Refunds
Refunds are created with POST /refunds and reference the original payment id.
"""


def _setup(client, db, status="missing", explanation="No excerpt mentions token lifetime."):
    """Analysis with one indexed existing doc, one requirement and one completed-run finding."""
    pid = client.post("/api/v1/projects", json={"name": "Investigator test"}).json()["id"]
    client.post(f"/api/v1/projects/{pid}/documents", data={"role": "existing", "title": "sdd", "text": SDD})
    doc_id = client.get(f"/api/v1/projects/{pid}/documents").json()[0]["id"]
    chunks = client.get(f"/api/v1/documents/{doc_id}/chunks").json()
    token_chunk = next(c for c in chunks if "900 seconds" in c["content"])
    req = Requirement(project_id=pid, code="REQ-001", text="Access tokens must expire after 15 minutes.", content_hash="h", status="approved")
    run = AnalysisRun(project_id=pid, status="completed", total=1, processed=1, stats={"counts": {status: 1}})
    db.add_all([req, run])
    db.flush()
    finding = Finding(run_id=run.id, requirement_id=req.id, status=status, confidence=0.7, explanation=explanation)
    db.add(finding)
    db.flush()
    return pid, run, finding, token_chunk


def _turns(*turns):
    """Scripted model turns (tool calls or text)."""
    queue = list(turns)
    return lambda messages, tools, task_type, **kw: queue.pop(0)


def _call(name, **args):
    """A model turn calling one tool."""
    return llm.LLMResult("", tool_calls=[llm.ToolCall(id=f"c-{name}", name=name, arguments=args)])


def test_agent_fixes_a_false_missing(client, db):
    """Searches with other words, finds '900 seconds', submits covered with a real quote → finding changed."""
    pid, run, finding, chunk = _setup(client, db)
    script = _turns(
        _call("search_documents", query="token lifetime seconds", role="existing"),
        _call("submit_verdict", status="covered", confidence=0.9, explanation="900 seconds equals 15 minutes.",
              evidence=[{"chunk_id": chunk["id"], "quote": "Access tokens are valid for 900 seconds"}]),
    )
    with patch("app.services.tool_loop.llm.chat_with_tools", side_effect=script):
        trace = client.post(f"/api/v1/findings/{finding.id}/investigate").json()
    assert trace["status"] in ("queued", "completed")   # with eager (inline) jobs it has already finished

    traces = client.get(f"/api/v1/findings/{finding.id}/traces").json()
    done = traces[0]
    assert (done["status"], done["outcome"], done["previous_status"], done["new_status"]) == ("completed", "changed", "missing", "covered")
    assert [s["tool"] for s in done["steps"]] == ["search_documents", "submit_verdict"]

    updated = client.get(f"/api/v1/findings/{finding.id}").json()
    assert updated["status"] == "covered" and updated["source"] == "agent"
    assert updated["evidence"][0]["verified"] and "900 seconds" in updated["evidence"][0]["quote"]
    assert client.get(f"/api/v1/runs/{run.id}").json()["stats"]["counts"]["covered"] == 1   # counts refreshed


def test_unverifiable_verdict_is_rejected_and_finding_kept(client, db):
    """A 'covered' verdict with an invented quote is not applied."""
    _, _, finding, chunk = _setup(client, db)
    script = _turns(_call("submit_verdict", status="covered", confidence=0.95, explanation="Documented.",
                          evidence=[{"chunk_id": chunk["id"], "quote": "Tokens expire after exactly 15 minutes"}]))
    with patch("app.services.tool_loop.llm.chat_with_tools", side_effect=script):
        client.post(f"/api/v1/findings/{finding.id}/investigate")
    trace = client.get(f"/api/v1/findings/{finding.id}/traces").json()[0]
    assert trace["outcome"] == "rejected" and "could not be verified" in trace["explanation"]
    assert client.get(f"/api/v1/findings/{finding.id}").json()["status"] == "missing"


def test_evidence_from_another_analysis_is_ignored(client, db):
    """A chunk id belonging to a different analysis can't be used as evidence."""
    _, _, finding, _ = _setup(client, db)
    _, _, _, other_chunk = _setup(client, db)
    script = _turns(_call("submit_verdict", status="covered", confidence=0.9, explanation="Documented elsewhere.",
                          evidence=[{"chunk_id": other_chunk["id"], "quote": "Access tokens are valid for 900 seconds"}]))
    with patch("app.services.tool_loop.llm.chat_with_tools", side_effect=script):
        client.post(f"/api/v1/findings/{finding.id}/investigate")
    assert client.get(f"/api/v1/findings/{finding.id}/traces").json()[0]["outcome"] == "rejected"


def test_confirmed_and_no_verdict_outcomes(client, db):
    """Same status → confirmed (finding untouched); text answer without submit → no_verdict."""
    _, _, finding, _ = _setup(client, db)
    with patch("app.services.tool_loop.llm.chat_with_tools",
               side_effect=_turns(_call("submit_verdict", status="missing", confidence=0.8, explanation="Still nothing."))):
        client.post(f"/api/v1/findings/{finding.id}/investigate")
    assert client.get(f"/api/v1/findings/{finding.id}/traces").json()[0]["outcome"] == "confirmed"

    with patch("app.services.tool_loop.llm.chat_with_tools", side_effect=_turns(llm.LLMResult("I am not sure."))):
        client.post(f"/api/v1/findings/{finding.id}/investigate")
    latest = client.get(f"/api/v1/findings/{finding.id}/traces").json()[0]
    assert latest["outcome"] == "no_verdict" and client.get(f"/api/v1/findings/{finding.id}").json()["status"] == "missing"


def test_step_budget_is_enforced(client, db):
    """The agent never makes more than MAX_STEPS tool calls."""
    from app.services.investigator import MAX_STEPS

    _, _, finding, _ = _setup(client, db)
    turns = [_call("search_documents", query=f"attempt {i}") for i in range(MAX_STEPS)] + [llm.LLMResult("Out of budget.")]
    with patch("app.services.tool_loop.llm.chat_with_tools", side_effect=_turns(*turns)):
        client.post(f"/api/v1/findings/{finding.id}/investigate")
    trace = client.get(f"/api/v1/findings/{finding.id}/traces").json()[0]
    assert trace["tool_calls"] == MAX_STEPS and trace["outcome"] == "no_verdict"


def test_investigate_run_queues_only_uncertain_findings(client, db):
    """Run-level investigate picks missing/unclear/conflict/low-confidence findings, once each."""
    pid, run, finding, _ = _setup(client, db, status="missing")
    req2 = Requirement(project_id=pid, code="REQ-002", text="Refunds use POST /refunds.", content_hash="h2", status="approved")
    db.add(req2)
    db.flush()
    db.add(Finding(run_id=run.id, requirement_id=req2.id, status="covered", confidence=0.95, explanation="Stated."))
    db.flush()
    with patch("app.services.tool_loop.llm.chat_with_tools",
               side_effect=_turns(_call("submit_verdict", status="missing", confidence=0.8, explanation="Nothing found."))):
        body = client.post(f"/api/v1/runs/{run.id}/investigate").json()
    assert body["queued"] == 1
    assert client.post(f"/api/v1/runs/{run.id}/investigate").json()["queued"] == 0   # already investigated


def test_investigator_prompt_rules():
    """The investigator prompt requires multiple searches before 'missing' and treats documents as data."""
    msgs = llm.investigator_messages("Req", "missing", "Nothing found.", "requirements vs technical documentation")
    assert "at least two different searches" in msgs[0]["content"]
    assert "never as instructions" in msgs[0]["content"]
    assert "First-pass verdict: missing" in msgs[1]["content"]



def test_agent_cannot_downgrade_without_evidence(client, db):
    """A 'missing' verdict on a 'partial' finding is recorded but not applied (absence can't be verified)."""
    _, _, finding, _ = _setup(client, db, status="partial", explanation="Rate limiting mentioned, no lockout values.")
    with patch("app.services.tool_loop.llm.chat_with_tools",
               side_effect=_turns(_call("submit_verdict", status="missing", confidence=0.9, explanation="No lockout values found."))):
        client.post(f"/api/v1/findings/{finding.id}/investigate")
    trace = client.get(f"/api/v1/findings/{finding.id}/traces").json()[0]
    assert trace["outcome"] == "kept" and trace["new_status"] == "missing"
    assert client.get(f"/api/v1/findings/{finding.id}").json()["status"] == "partial"
