"""
Gap analysis pipeline.

  Stage 1  Retrieval (deterministic)   top-k evidence chunks from EXISTING documents per requirement
  Stage 2  Classification (LLM)        several requirements per call, schema-validated
  Stage 3  Guardrails (deterministic)  quotes verified against the source, status rules enforced
  (Stage 4 — the investigator agent for unclear/conflict findings — is added in Phase 10)

Re-analysis is cheap: each finding stores a cache key built from everything that
determines its result (requirement text, evidence chunk ids, prompt version, model,
preset). If an identical key exists from an earlier completed run, the finding is
copied instead of calling the LLM again.
"""
import hashlib
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload

from app import llm
from app.core.config import settings
from app.models import AnalysisRun, Evidence, Finding, LlmCall, Project, Requirement
from app.services import retrieval
from app.services.evidence_verifier import verify_quote
from app.services.project_service import get_project_or_404

logger = logging.getLogger(__name__)

NEEDS_EVIDENCE = ("covered", "partial", "conflict")


@dataclass
class _Item:
    """One requirement moving through the pipeline."""
    requirement: Requirement
    hits: list[retrieval.ScoredChunk] = field(default_factory=list)
    cache_key: str = ""

    @property
    def top_score(self) -> float:
        """Best retrieval similarity for this requirement (0 when nothing was found)."""
        return max((h.score for h in self.hits), default=0.0)


# ── Start ─────────────────────────────────────────────────────────────────────

def start_analysis(project_id: UUID, db: Session) -> AnalysisRun:
    """Check preconditions, create a queued run and hand it to the worker."""
    project = get_project_or_404(project_id, db)
    approved = db.execute(select(Requirement.id).where(
        Requirement.project_id == project.id, Requirement.status == "approved")).scalars().all()
    if not approved:
        raise HTTPException(status_code=422, detail="Approve at least one requirement before running the analysis.")
    existing_docs = [d for d in project.documents if d.role == "existing"]
    if not any(d.status == "indexed" for d in existing_docs):
        raise HTTPException(status_code=422, detail="Upload at least one existing document and wait until it is indexed.")
    if any(d.status in ("uploaded", "processing") for d in project.documents):
        raise HTTPException(status_code=409, detail="Some documents are still processing — try again shortly.")
    if any(r.status in ("queued", "running") for r in project.runs):
        raise HTTPException(status_code=409, detail="An analysis is already running for this project.")

    run = AnalysisRun(
        project_id=project.id, status="queued", total=len(approved),
        model=llm.model_label("classify_requirements"),
        prompt_version=llm.PROMPT_VERSIONS["classify_requirements"],
    )
    db.add(run)
    db.commit()

    try:
        from app.tasks import run_analysis as task   # inside the try: a broken queue setup must not crash the request

        task.delay(str(run.id))
    except Exception as exc:
        logger.warning("Could not enqueue analysis run %s: %s", run.id, exc)
        run.status = "failed"
        run.error_message = "Processing queue unavailable — try again."
        db.commit()
    db.refresh(run)
    return run


# ── Pipeline ──────────────────────────────────────────────────────────────────

REWRITE_BATCH = 10   # requirements per query-rewriting call


def retrieve_for_requirements(project_id: UUID, requirements: list[Requirement], db: Session,
                              stats: dict | None = None) -> dict[UUID, list[retrieval.ScoredChunk]]:
    """Stage 1 for a set of requirements: hybrid search, then LLM query rewriting for weak matches only.

    Shared by the pipeline and the evaluation harness so both measure the same retrieval.
    """
    stats = stats if stats is not None else {}
    hits = {r.id: retrieval.search_evidence(project_id, r.text, db) for r in requirements}

    if settings.QUERY_REWRITE and settings.RETRIEVAL_MODE == "hybrid":
        weak = [r for r in requirements
                if max((h.score for h in hits[r.id]), default=0.0) < settings.REWRITE_BELOW_SCORE]
        for start in range(0, len(weak), REWRITE_BATCH):
            batch = weak[start:start + REWRITE_BATCH]
            labels = {f"R{i + 1}": r for i, r in enumerate(batch)}
            stats["rewrite_calls"] = stats.get("rewrite_calls", 0) + 1
            alternatives = llm.rewrite_queries([{"id": lab, "text": r.text} for lab, r in labels.items()])
            for lab, req in labels.items():
                if alternatives.get(lab):
                    hits[req.id] = retrieval.search_evidence(project_id, req.text, db, extra_queries=alternatives[lab])
                    stats["rewritten"] = stats.get("rewritten", 0) + 1
    return hits


def _cache_key(item: _Item, project: Project, run: AnalysisRun) -> str:
    """Hash of every input that determines a finding — identical inputs give an identical result."""
    chunk_ids = ",".join(sorted(str(h.chunk.id) for h in item.hits))
    raw = "|".join([item.requirement.content_hash, chunk_ids, run.prompt_version or "", run.model or "", project.preset])
    return hashlib.sha256(raw.encode()).hexdigest()


def _cached_finding(key: str, project_id: UUID, db: Session) -> Finding | None:
    """Most recent finding with this cache key from a completed run of the same project."""
    return db.execute(
        select(Finding)
        .join(AnalysisRun, Finding.run_id == AnalysisRun.id)
        .where(Finding.cache_key == key, AnalysisRun.project_id == project_id, AnalysisRun.status == "completed")
        .options(selectinload(Finding.evidence))
        .order_by(Finding.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()


def _copy_cached(cached: Finding, item: _Item, run: AnalysisRun, db: Session) -> Finding:
    """Store a copy of a cached finding (and its evidence) under the new run."""
    finding = Finding(
        run_id=run.id, requirement_id=item.requirement.id, status=cached.status, confidence=cached.confidence,
        explanation=cached.explanation, missing_detail=cached.missing_detail,
        suggested_action=cached.suggested_action, source="cache", cache_key=item.cache_key,
    )
    finding.evidence = [Evidence(chunk_id=e.chunk_id, quote=e.quote, verified=e.verified, score=e.score)
                        for e in cached.evidence]
    db.add(finding)
    return finding


def _excerpt_source(hit: retrieval.ScoredChunk) -> str:
    """Short citation shown to the model next to each excerpt."""
    parts = [hit.document.filename]
    if hit.chunk.section:
        parts.append(f'section "{hit.chunk.section}"')
    if hit.chunk.page_start:
        parts.append(f"p.{hit.chunk.page_start}")
    return ", ".join(parts)


def apply_guardrails(result: llm.Classification, item: _Item, labels: dict[str, retrieval.ScoredChunk]):
    """Verify quotes and enforce status rules. Returns (status, explanation, evidence rows, dropped count)."""
    evidence, dropped = [], 0
    for ev in result.evidence:
        hit = labels.get(ev.chunk.strip().upper())
        if hit is None:
            dropped += 1
            continue
        check = verify_quote(ev.quote, hit.chunk.content)
        if not check.verified:
            dropped += 1
            continue
        evidence.append(Evidence(chunk_id=hit.chunk.id, quote=check.text, verified=True, score=round(hit.score, 4)))

    status, explanation = result.status, result.explanation
    if status in NEEDS_EVIDENCE and not evidence:
        status = "unclear"
        explanation += " [Downgraded to unclear: the cited evidence could not be found in the source documents.]"
    elif status == "missing" and item.top_score >= settings.MISSING_GUARD_SCORE:
        status = "unclear"
        explanation += (" [Downgraded from missing to unclear: closely related text exists in the documents "
                        f"(similarity {item.top_score:.2f}), so a human should confirm.]")
    if status == "missing":
        evidence = []
    return status, explanation, evidence, dropped


def _error_finding(item: _Item, run: AnalysisRun, reason: str) -> Finding:
    """A finding recorded when the model could not classify the requirement — the run still completes."""
    return Finding(
        run_id=run.id, requirement_id=item.requirement.id, status="unclear", confidence=0.0,
        explanation=f"Could not be analysed automatically: {reason}",
        suggested_action="Re-run the analysis or review this requirement manually.",
        source="pipeline", cache_key=None,
    )


def _classify_batch(batch: list[_Item], project: Project, run: AnalysisRun, db: Session, stats: dict) -> None:
    """One LLM call for a batch of requirements, then guardrails, then persist."""
    labels: dict[str, retrieval.ScoredChunk] = {}
    by_chunk: dict[UUID, str] = {}
    for item in batch:
        for hit in item.hits:
            if hit.chunk.id not in by_chunk:
                label = f"C{len(labels) + 1}"
                by_chunk[hit.chunk.id] = label
                labels[label] = hit
    req_labels = {f"R{i + 1}": item for i, item in enumerate(batch)}

    try:
        stats["llm_calls"] += 1
        results = llm.classify_requirements(
            [{"id": rid, "text": item.requirement.text} for rid, item in req_labels.items()],
            [{"id": lab, "source": _excerpt_source(hit), "text": hit.chunk.content} for lab, hit in labels.items()],
            project.preset,
        )
    except (llm.LLMOutputError, HTTPException) as exc:
        reason = exc.detail if isinstance(exc, HTTPException) else str(exc)
        logger.warning("Classification batch failed in run %s: %s", run.id, reason)
        stats["errors"] += len(batch)
        for item in batch:
            db.add(_error_finding(item, run, str(reason)[:300]))
        return

    by_id = {r.id.strip().upper(): r for r in results}
    for rid, item in req_labels.items():
        result = by_id.get(rid)
        if result is None:
            stats["errors"] += 1
            db.add(_error_finding(item, run, "the model returned no result for this requirement"))
            continue
        status, explanation, evidence, dropped = apply_guardrails(result, item, labels)
        stats["evidence_dropped"] += dropped
        finding = Finding(
            run_id=run.id, requirement_id=item.requirement.id, status=status,
            confidence=round(result.confidence, 3) if status == result.status else min(result.confidence, 0.5),
            explanation=explanation, missing_detail=result.missing_detail,
            suggested_action=result.suggested_action, source="pipeline", cache_key=item.cache_key,
        )
        finding.evidence = evidence
        db.add(finding)


def run_analysis(run_id: str | UUID, db: Session) -> None:
    """Background job body. Every LLM call inside is tagged with the run id for token accounting."""
    with llm.call_context(f"run:{run_id}"):
        _run_analysis(run_id, db)


def _token_usage(context: str, db: Session) -> dict:
    """Sum tokens and provider attempts logged in llm_calls for one job context."""
    prompt, completion, attempts = db.execute(
        select(func.coalesce(func.sum(LlmCall.prompt_tokens), 0),
               func.coalesce(func.sum(LlmCall.completion_tokens), 0),
               func.count(LlmCall.id))
        .where(LlmCall.context == context)
    ).one()
    return {"prompt_tokens": int(prompt), "completion_tokens": int(completion), "provider_attempts": int(attempts)}


def _run_analysis(run_id: str | UUID, db: Session) -> None:
    """Pipeline body. Idempotent: a redelivered run clears its partial findings and starts again."""
    run = db.get(AnalysisRun, UUID(str(run_id)))
    if run is None or run.status == "completed":
        return
    project = db.get(Project, run.project_id)
    started = time.perf_counter()
    stats = {"llm_calls": 0, "cache_hits": 0, "errors": 0, "evidence_dropped": 0}
    try:
        db.execute(delete(Finding).where(Finding.run_id == run.id))
        run.status, run.processed, run.error_message = "running", 0, None
        run.started_at = datetime.now(timezone.utc)
        db.commit()

        requirements = db.execute(select(Requirement).where(
            Requirement.project_id == project.id, Requirement.status == "approved").order_by(Requirement.code)).scalars().all()
        run.total = len(requirements)

        # Stage 1 — retrieval (+ query rewriting for weak matches) + cache lookup
        all_hits = retrieve_for_requirements(project.id, requirements, db, stats)
        pending: list[_Item] = []
        for req in requirements:
            item = _Item(requirement=req, hits=all_hits[req.id])
            item.cache_key = _cache_key(item, project, run)
            cached = _cached_finding(item.cache_key, project.id, db)
            if cached is not None:
                _copy_cached(cached, item, run, db)
                stats["cache_hits"] += 1
                run.processed += 1
            else:
                pending.append(item)
        db.commit()

        # Stage 2 + 3 — batched classification with guardrails; commit after each batch for live progress
        size = max(1, settings.ANALYSIS_BATCH_SIZE)
        for start in range(0, len(pending), size):
            batch = pending[start:start + size]
            _classify_batch(batch, project, run, db, stats)
            run.processed += len(batch)
            db.commit()

        if run.total and stats["errors"] == run.total:
            raise RuntimeError("Every requirement failed to classify — check the AI provider configuration.")

        counts = {s: 0 for s in llm.FindingStatus.__args__}
        for status in db.execute(select(Finding.status).where(Finding.run_id == run.id)).scalars():
            counts[status] += 1
        stats["counts"] = counts
        stats.update(_token_usage(f"run:{run.id}", db))
        stats["duration_s"] = round(time.perf_counter() - started, 1)
        run.stats = stats
        run.status = "completed"
        run.finished_at = datetime.now(timezone.utc)
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.exception("Analysis run %s failed", run_id)
        run.status = "failed"
        run.error_message = str(getattr(exc, "detail", exc))[:500]
        stats["duration_s"] = round(time.perf_counter() - started, 1)
        run.stats = stats
        run.finished_at = datetime.now(timezone.utc)
        db.commit()
