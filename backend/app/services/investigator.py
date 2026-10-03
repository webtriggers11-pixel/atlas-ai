"""
Investigator agent (Phase 10) — re-checks ONE uncertain finding with a bounded tool loop.

Why an agent here (and only here): the main pipeline is a fixed recipe — top-4 passages,
one classification. That recipe is cheap and right most of the time, but evaluation showed
its main error is a false "missing" when the evidence uses different words. Deciding WHAT to
search next based on what was just found is exactly what a fixed pipeline can't do, so the
agent is used only for the findings most likely to be wrong:
    missing · unclear · conflict · or confidence below 0.6

Safety rails:
- read-only tools (search_documents, get_chunk), analysis-scoped on the server
- at most MAX_STEPS tool calls; the verdict comes through a validated submit_verdict tool
- the verdict passes the SAME quote verification as the pipeline; if its evidence can't be
  verified, the original finding is kept (outcome "rejected")
- asymmetric authority: the agent may only CHANGE a finding when it brings verified evidence
  (→ covered / partial / conflict). A claim that something is absent ("missing"/"unclear") can't be
  verified, so such a downgrade is recorded but not applied (outcome "kept"). Measured reason: in live
  tests a small model downgraded a correct "partial" to "missing" despite finding related text.
- every step is stored in agent_traces so a human can audit what the agent did
"""
import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app import llm
from app.core.security import ensure_owner
from app.models import AgentTrace, DocChunk, Evidence, Finding, LlmCall, ProjectDocument
from app.services.chat_service import build_tools
from app.services.evidence_verifier import verify_quote
from app.services.tool_loop import Tool, run_tool_loop

logger = logging.getLogger(__name__)

MAX_STEPS = 6
LOW_CONFIDENCE = 0.6
NEEDS_EVIDENCE = ("covered", "partial", "conflict")


def is_uncertain(finding: Finding) -> bool:
    """Findings worth a second, deeper look."""
    return finding.status in ("missing", "unclear", "conflict") or (finding.confidence is not None and finding.confidence < LOW_CONFIDENCE)


def get_finding_or_404(finding_id: UUID, db: Session) -> Finding:
    """Fetch a finding (with run and requirement) or raise 404."""
    finding = db.get(Finding, finding_id)
    if finding is None:
        raise HTTPException(status_code=404, detail=f"Finding {finding_id} not found.")
    ensure_owner(finding.run.project.owner_id)
    return finding


def _enqueue(trace: AgentTrace, db: Session) -> None:
    """Queue the investigation; mark the trace failed (visibly) if the queue can't take it."""
    try:
        from app.tasks import investigate_finding as task   # inside the try: a broken queue must not 500
        task.delay(str(trace.id))
    except Exception as exc:
        logger.warning("Could not enqueue investigation %s: %s", trace.id, exc)
        trace.status, trace.outcome, trace.error = "failed", "error", "Processing queue unavailable — try again."
        db.commit()


def start_investigation(finding_id: UUID, db: Session) -> AgentTrace:
    """Create a trace for one finding and queue the agent."""
    finding = get_finding_or_404(finding_id, db)
    if finding.run.status != "completed":
        raise HTTPException(status_code=409, detail="Only findings of a completed run can be investigated.")
    if any(t.status in ("queued", "running") for t in finding.traces):
        raise HTTPException(status_code=409, detail="This finding is already being investigated.")
    trace = AgentTrace(finding_id=finding.id, status="queued", previous_status=finding.status)
    db.add(trace)
    db.commit()
    _enqueue(trace, db)
    db.refresh(trace)
    return trace


def start_run_investigation(run_id: UUID, db: Session) -> list[AgentTrace]:
    """Queue the agent for every uncertain, not-yet-investigated finding of a run."""
    from app.services.findings_service import get_run_or_404

    run = get_run_or_404(run_id, db)
    if run.status != "completed":
        raise HTTPException(status_code=409, detail="Run the analysis to completion first.")
    findings = db.execute(select(Finding).where(Finding.run_id == run.id).options(selectinload(Finding.traces))).scalars().all()
    traces = []
    for f in findings:
        if is_uncertain(f) and not f.traces:
            trace = AgentTrace(finding_id=f.id, status="queued", previous_status=f.status)
            db.add(trace)
            traces.append(trace)
    db.commit()
    for trace in traces:
        _enqueue(trace, db)
    return traces


def _verify(verdict: llm.Verdict, project_id: UUID, db: Session) -> list[Evidence]:
    """Keep only evidence whose chunk belongs to this analysis and whose quote really appears in it."""
    kept = []
    for ev in verdict.evidence:
        try:
            chunk_id = UUID(ev.chunk_id)
        except ValueError:
            continue
        chunk = db.execute(
            select(DocChunk).join(ProjectDocument, DocChunk.document_id == ProjectDocument.id)
            .where(DocChunk.id == chunk_id, ProjectDocument.project_id == project_id, ProjectDocument.role == "existing")
        ).scalar_one_or_none()
        if chunk is None:
            continue
        check = verify_quote(ev.quote, chunk.content)
        if check.verified:
            kept.append(Evidence(chunk_id=chunk.id, quote=check.text, verified=True))
    return kept


def _recount(run_id: UUID, db: Session) -> None:
    """Refresh the run's per-status counts after the agent changed a finding."""
    from app.models import AnalysisRun

    run = db.get(AnalysisRun, run_id)
    counts = {s: 0 for s in llm.FindingStatus.__args__}
    for status in db.execute(select(Finding.status).where(Finding.run_id == run_id)).scalars():
        counts[status] += 1
    run.stats = {**(run.stats or {}), "counts": counts}


def run_investigation(trace_id: str | UUID, db: Session) -> None:
    """Background job body: investigate, verify, apply (or keep the original), record the trace."""
    trace = db.get(AgentTrace, UUID(str(trace_id)))
    if trace is None or trace.status in ("completed", "failed"):
        return
    finding = trace.finding
    project_id = finding.run.project_id
    trace.status = "running"
    db.commit()

    started = datetime.now(timezone.utc)
    try:
        project = finding.run.project
        kind = "resume vs job description" if project.preset == "resume_jd" else "requirements vs technical documentation"
        tools = [t for t in build_tools(project_id, db, compact=True) if t.name in ("search_documents", "get_chunk")]
        submit = Tool("submit_verdict", "Submit your final verdict for this requirement (call exactly once).", llm.Verdict, lambda a: None)
        messages = llm.investigator_messages(finding.requirement.text, finding.status, finding.explanation, kind)

        with llm.call_context(f"agent:{trace.id}"):
            result = run_tool_loop(messages, tools, task_type="investigate", max_tool_calls=MAX_STEPS,
                                   finish_tool=submit, retry_budget_s=llm.settings.LLM_BACKGROUND_RETRY_BUDGET_S,
                                   max_result_chars=2500, keep_full_results=2)

        trace.steps = [{"tool": s.tool, "arguments": s.arguments, "ok": s.ok, "summary": s.summary} for s in result.steps]
        trace.tool_calls = len(result.steps)
        verdict = result.finish_args

        if verdict is None:
            trace.outcome = "no_verdict"
            trace.explanation = result.answer[:1200] or "The agent did not submit a verdict within its step budget."
        else:
            trace.new_status = verdict.status
            trace.explanation = verdict.explanation
            evidence = _verify(verdict, project_id, db)
            if verdict.status in NEEDS_EVIDENCE and not evidence:
                trace.outcome = "rejected"   # unverifiable claim: keep the pipeline's finding
                trace.explanation = f"{verdict.explanation} [Not applied: the cited evidence could not be verified in the documents.]"
            elif verdict.status == finding.status:
                trace.outcome = "confirmed"
            elif verdict.status not in NEEDS_EVIDENCE:
                trace.outcome = "kept"   # an unverifiable absence claim never overrides the pipeline
                trace.explanation = (f"{verdict.explanation} [Not applied: the agent can only change a finding "
                                     "when it brings verified evidence.]")
            else:
                trace.outcome = "changed"
                finding.status = verdict.status
                finding.confidence = round(verdict.confidence, 3)
                finding.explanation = f"{verdict.explanation} [Re-checked by the investigator agent; first pass said {trace.previous_status}.]"
                finding.missing_detail = verdict.missing_detail
                finding.suggested_action = verdict.suggested_action
                finding.source = "agent"
                finding.cache_key = None   # an agent result is not a pure function of the cache inputs
                finding.evidence = [] if verdict.status == "missing" else evidence
                db.flush()
                _recount(finding.run_id, db)

        tokens = db.execute(
            select(func.coalesce(func.sum(LlmCall.prompt_tokens), 0), func.coalesce(func.sum(LlmCall.completion_tokens), 0))
            .where(LlmCall.context == f"agent:{trace.id}")
        ).one()
        trace.prompt_tokens, trace.completion_tokens = int(tokens[0]), int(tokens[1])
        trace.status = "completed"
    except Exception as exc:
        db.rollback()
        logger.exception("Investigation %s failed", trace_id)
        trace = db.get(AgentTrace, UUID(str(trace_id)))
        trace.status, trace.outcome = "failed", "error"
        trace.error = str(getattr(exc, "detail", exc))[:500]
    trace.finished_at = datetime.now(timezone.utc)
    trace.duration_s = round((trace.finished_at - started).total_seconds(), 1)
    db.commit()
