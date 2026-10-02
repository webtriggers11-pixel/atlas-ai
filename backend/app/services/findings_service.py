"""
Findings service — read analysis runs and their findings with evidence.
(The pipeline that *creates* runs and findings lives in analysis_service.)
"""
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import AnalysisRun, Finding, Evidence, DocChunk, Requirement
from app.schemas.project import FindingResponse, EvidenceResponse, RequirementRef
from app.services.project_service import get_project_or_404


def get_run_or_404(run_id: UUID, db: Session) -> AnalysisRun:
    """Fetch an analysis run by id or raise 404."""
    run = db.get(AnalysisRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Analysis run {run_id} not found.")
    return run


def list_runs(project_id: UUID, db: Session) -> list[AnalysisRun]:
    """Return a project's runs, newest first."""
    get_project_or_404(project_id, db)
    return db.execute(
        select(AnalysisRun).where(AnalysisRun.project_id == project_id).order_by(AnalysisRun.created_at.desc())
    ).scalars().all()


def _finding_query():
    """Base query that eagerly loads everything a FindingResponse needs (avoids N+1 queries)."""
    return select(Finding).options(
        selectinload(Finding.requirement).selectinload(Requirement.source_chunk).selectinload(DocChunk.document),
        selectinload(Finding.evidence).selectinload(Evidence.chunk).selectinload(DocChunk.document),
    )


def to_finding_response(finding: Finding) -> FindingResponse:
    """Convert a Finding ORM row (with loaded relationships) into its API shape."""
    req = finding.requirement
    return FindingResponse(
        id=finding.id,
        run_id=finding.run_id,
        requirement=RequirementRef(
            id=req.id, code=req.code, text=req.text, section=req.section,
            source_document=req.source_chunk.document.filename if req.source_chunk else None,
            source_page=req.source_chunk.page_start if req.source_chunk else None,
        ),
        status=finding.status,
        confidence=finding.confidence,
        explanation=finding.explanation,
        missing_detail=finding.missing_detail,
        suggested_action=finding.suggested_action,
        source=finding.source,
        evidence=[
            EvidenceResponse(
                id=e.id,
                chunk_id=e.chunk_id,
                document_id=e.chunk.document_id,
                document_filename=e.chunk.document.filename,
                document_role=e.chunk.document.role,
                section=e.chunk.section,
                page_start=e.chunk.page_start,
                quote=e.quote,
                verified=e.verified,
                score=e.score,
            )
            for e in finding.evidence
        ],
        created_at=finding.created_at,
        updated_at=finding.updated_at,
    )


def list_findings(run_id: UUID, status: str | None, db: Session) -> list[FindingResponse]:
    """Return a run's findings ordered by requirement code, optionally filtered by status."""
    get_run_or_404(run_id, db)
    query = _finding_query().join(Finding.requirement).where(Finding.run_id == run_id)
    if status:
        query = query.where(Finding.status == status)
    findings = db.execute(query.order_by(Requirement.code)).scalars().all()
    return [to_finding_response(f) for f in findings]


def get_finding_or_404(finding_id: UUID, db: Session) -> Finding:
    """Fetch one finding with requirement and evidence loaded, or raise 404."""
    finding = db.execute(_finding_query().where(Finding.id == finding_id)).scalar_one_or_none()
    if finding is None:
        raise HTTPException(status_code=404, detail=f"Finding {finding_id} not found.")
    return finding
