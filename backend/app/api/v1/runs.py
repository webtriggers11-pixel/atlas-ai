from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.project import RunResponse, FindingResponse, FindingStatus
from app.services import findings_service

router = APIRouter(tags=["analysis"])


# GET /api/v1/runs/{run_id}
# Example response: {"id": "...", "status": "running", "total": 24, "processed": 9, ...}
@router.get("/runs/{run_id}", response_model=RunResponse)
def get_run(run_id: UUID, db: Session = Depends(get_db)):
    """Get one analysis run — the UI polls this for the progress bar."""
    return findings_service.get_run_or_404(run_id, db)


# GET /api/v1/runs/{run_id}/findings?status=missing
# Example response: [{"id": "...", "requirement": {"code": "REQ-004", ...}, "status": "missing",
#                     "explanation": "...", "evidence": []}]
@router.get("/runs/{run_id}/findings", response_model=list[FindingResponse])
def list_findings(run_id: UUID, status: Optional[FindingStatus] = None, db: Session = Depends(get_db)):
    """List a run's findings with their evidence."""
    return findings_service.list_findings(run_id, status, db)


# GET /api/v1/findings/{finding_id}
# Example response: {"id": "...", "status": "partial", "evidence": [{"quote": "...", "verified": true, ...}]}
@router.get("/findings/{finding_id}", response_model=FindingResponse)
def get_finding(finding_id: UUID, db: Session = Depends(get_db)):
    """Get one finding with all its evidence."""
    return findings_service.to_finding_response(findings_service.get_finding_or_404(finding_id, db))
