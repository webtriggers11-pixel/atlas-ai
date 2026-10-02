"""
Requirement extraction job — turns indexed reference documents into a reviewable
list of draft requirements (REQ-001 ...).

Flow:
  reference chunks (overlap removed) → batches of ~1200 words with section tags
  → llm.extract_requirements per batch → dedupe (exact hash + near-duplicate vectors)
  → link each requirement to the chunk it most likely came from → insert as drafts.

Re-running replaces only *unreviewed* extracted drafts; anything the user approved,
rejected or typed by hand is kept and new extractions are deduplicated against it.
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID

import numpy as np
from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app import llm
from app.models import DocChunk, Project, ProjectDocument, Requirement
from app.services.embedding_service import embed_texts
from app.services.project_service import get_project_or_404
from app.services.requirement_service import next_codes, requirement_hash

logger = logging.getLogger(__name__)

BATCH_WORDS = 1200          # input words per LLM call — big enough for context, small enough for free tiers
NEAR_DUPLICATE = 0.93       # cosine similarity above which two requirements are treated as the same


@dataclass
class _Batch:
    text: str
    chunks: list[DocChunk] = field(default_factory=list)


def _strip_overlap(previous: str, current: str, max_words: int = 80) -> str:
    """Remove the words at the start of `current` that repeat the end of `previous` (chunk overlap)."""
    prev_words, cur_words = previous.split(), current.split()
    for n in range(min(max_words, len(prev_words), len(cur_words)), 0, -1):
        if prev_words[-n:] == cur_words[:n]:
            return " ".join(cur_words[n:])
    return current


def build_batches(chunks: list[DocChunk], batch_words: int = BATCH_WORDS) -> list[_Batch]:
    """Group chunks (in document order) into LLM-sized batches, each section wrapped in a <section> tag."""
    batches: list[_Batch] = []
    current = _Batch(text="")
    words = 0
    previous: DocChunk | None = None

    for chunk in chunks:
        same_doc = previous is not None and previous.document_id == chunk.document_id
        body = _strip_overlap(previous.content, chunk.content) if same_doc else chunk.content
        previous = chunk
        if not body.strip():
            continue
        n = len(body.split())
        if current.chunks and words + n > batch_words:
            batches.append(current)
            current, words = _Batch(text=""), 0
        title = (chunk.section or "").replace('"', "'")
        current.text += f'<section title="{title}">{body}</section>\n'
        current.chunks.append(chunk)
        words += n
    if current.chunks:
        batches.append(current)
    return batches


def start_extraction(project_id: UUID, db: Session) -> Project:
    """Validate preconditions, mark the project 'running' and queue the background job."""
    project = get_project_or_404(project_id, db)
    if project.extraction_status == "running":
        raise HTTPException(status_code=409, detail="Requirement extraction is already running.")

    reference = [d for d in project.documents if d.role == "reference"]
    if not any(d.status == "indexed" for d in reference):
        raise HTTPException(status_code=422, detail="Upload at least one reference document and wait until it is indexed.")
    if any(d.status in ("uploaded", "processing") for d in reference):
        raise HTTPException(status_code=409, detail="Some reference documents are still processing — try again shortly.")

    project.extraction_status = "running"
    project.extraction_error = None
    db.commit()

    from app.tasks import extract_requirements as task
    try:
        task.delay(str(project.id))
    except Exception as exc:
        logger.warning("Could not enqueue extraction for %s: %s", project.id, exc)
        project.extraction_status = "failed"
        project.extraction_error = "Processing queue unavailable — try again."
        db.commit()
    db.refresh(project)
    return project


def _dedupe(candidates: list[tuple[llm.ExtractedRequirement, _Batch]], existing: list[Requirement]):
    """Drop exact (normalized-text hash) and near-duplicate (cosine ≥ NEAR_DUPLICATE) requirements."""
    seen_hashes = {r.content_hash for r in existing}
    unique = []
    for req, batch in candidates:
        h = requirement_hash(req.text)
        if h not in seen_hashes:
            seen_hashes.add(h)
            unique.append((req, batch, h))
    if not unique:
        return [], None

    vectors = np.array(embed_texts([r.text for r, _, _ in unique] + [r.text for r in existing]))
    new_vecs, old_vecs = vectors[: len(unique)], vectors[len(unique):]
    kept, kept_vecs = [], []
    for i, item in enumerate(unique):
        v = new_vecs[i]
        if len(old_vecs) and float((old_vecs @ v).max()) >= NEAR_DUPLICATE:
            continue
        if kept_vecs and float((np.array(kept_vecs) @ v).max()) >= NEAR_DUPLICATE:
            continue
        kept.append(item)
        kept_vecs.append(v)
    return kept, np.array(kept_vecs)


def _best_source_chunk(req_vec: np.ndarray, batch: _Batch) -> DocChunk | None:
    """The chunk in the requirement's batch whose embedding is most similar to the requirement."""
    with_vectors = [c for c in batch.chunks if c.embedding is not None]
    if not with_vectors:
        return None
    scores = np.array([np.asarray(c.embedding) for c in with_vectors]) @ req_vec
    return with_vectors[int(scores.argmax())]


def run_extraction(project_id: str | UUID, db: Session) -> None:
    """The background job body (LLM calls tagged with the project for token accounting)."""
    with llm.call_context(f"extract:{project_id}"):
        _run_extraction(project_id, db)


def _run_extraction(project_id: str | UUID, db: Session) -> None:
    """Extraction body. Safe to re-run: it only replaces unreviewed extracted drafts."""
    project = db.get(Project, UUID(str(project_id)))
    if project is None:
        return
    try:
        chunks = db.execute(
            select(DocChunk)
            .join(ProjectDocument, DocChunk.document_id == ProjectDocument.id)
            .where(ProjectDocument.project_id == project.id, ProjectDocument.role == "reference",
                   ProjectDocument.status == "indexed")
            .order_by(ProjectDocument.created_at, DocChunk.chunk_index)
        ).scalars().all()
        batches = build_batches(chunks)

        candidates, failed_batches = [], 0
        for batch in batches:
            try:
                candidates += [(r, batch) for r in llm.extract_requirements(batch.text, project.preset)]
            except llm.LLMOutputError as exc:
                failed_batches += 1
                logger.warning("Extraction batch failed for project %s: %s", project.id, exc)
        if batches and failed_batches == len(batches):
            raise llm.LLMOutputError("The AI model returned unusable output for every part of the document.")

        db.execute(delete(Requirement).where(
            Requirement.project_id == project.id, Requirement.origin == "extracted", Requirement.status == "draft"))
        db.flush()
        existing = db.execute(select(Requirement).where(Requirement.project_id == project.id)).scalars().all()

        kept, vectors = _dedupe(candidates, existing)
        codes = next_codes(project.id, len(kept), db)
        for (req, batch, h), code, vec in zip(kept, codes, vectors if vectors is not None else []):
            source = _best_source_chunk(vec, batch)
            db.add(Requirement(
                project_id=project.id, code=code, text=req.text.strip(),
                section=req.section or (source.section if source else None),
                status="draft", origin="extracted", content_hash=h,
                source_chunk_id=source.id if source else None,
            ))

        project.extraction_status = "completed"
        project.extracted_at = datetime.now(timezone.utc)
        project.extraction_error = (
            f"{failed_batches} of {len(batches)} parts of the document could not be processed." if failed_batches else None
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.exception("Requirement extraction failed for %s", project_id)
        project.extraction_status = "failed"
        detail = exc.detail if hasattr(exc, "detail") else str(exc)
        project.extraction_error = f"Extraction failed: {str(detail)[:400]}"
        db.commit()
