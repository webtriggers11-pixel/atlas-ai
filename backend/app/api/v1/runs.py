import re
from typing import Literal, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Response, status as http_status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.project import RunResponse, FindingResponse, FindingStatus, TraceResponse, InvestigateRunResponse
from app.services import findings_service, investigator, report_service

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


# POST /api/v1/findings/{finding_id}/investigate
# Example response: 202 {"id": "<trace id>", "status": "queued", "previous_status": "missing", "tool_calls": 0, ...}
#   → poll GET /api/v1/findings/{finding_id}/traces until status is completed/failed
@router.post("/findings/{finding_id}/investigate", response_model=TraceResponse, status_code=http_status.HTTP_202_ACCEPTED)
def investigate_finding(finding_id: UUID, db: Session = Depends(get_db)):
    """Ask the investigator agent to re-check one finding with deeper, multi-step searching."""
    return investigator.start_investigation(finding_id, db)


# GET /api/v1/findings/{finding_id}/traces
# Example response: [{"id": "...", "status": "completed", "outcome": "changed", "previous_status": "missing",
#                     "new_status": "partial", "steps": [{"tool": "search_documents", "arguments": {...}, ...}], ...}]
@router.get("/findings/{finding_id}/traces", response_model=list[TraceResponse])
def list_traces(finding_id: UUID, db: Session = Depends(get_db)):
    """The agent's investigations of a finding, newest first."""
    return investigator.get_finding_or_404(finding_id, db).traces


# POST /api/v1/runs/{run_id}/investigate
# Example response: 202 {"queued": 4, "trace_ids": ["...", "..."]}
@router.post("/runs/{run_id}/investigate", response_model=InvestigateRunResponse, status_code=http_status.HTTP_202_ACCEPTED)
def investigate_run(run_id: UUID, db: Session = Depends(get_db)):
    """Re-check every uncertain finding (missing, unclear, conflict, low confidence) not yet investigated."""
    traces = investigator.start_run_investigation(run_id, db)
    return InvestigateRunResponse(queued=len(traces), trace_ids=[t.id for t in traces])


# GET /api/v1/runs/{run_id}/report
# Example response: {"analysis": {"name": "...", "type": "..."}, "summary": {"headline": "8 of 12 requirements (67%) ...",
#                    "counts": {...}}, "sections": {"missing": [...], "conflict": [...], ...}, "actions": [...]}
@router.get("/runs/{run_id}/report")
def get_report(run_id: UUID, db: Session = Depends(get_db)):
    """Structured report for a completed run (executive summary, gaps by type, actions, evidence)."""
    return report_service.build_report(run_id, db)


_EXPORTS = {
    "csv": ("text/csv; charset=utf-8", "csv"),
    "md": ("text/markdown; charset=utf-8", "md"),
    "pdf": ("application/pdf", "pdf"),
}


# GET /api/v1/runs/{run_id}/export?format=pdf
# Example response: a file download (traceability matrix CSV, Markdown report, or PDF report)
@router.get("/runs/{run_id}/export")
def export_run(run_id: UUID, format: Literal["csv", "md", "pdf"] = "csv", db: Session = Depends(get_db)):
    """Download the report as CSV, Markdown or PDF."""
    report = report_service.build_report(run_id, db)
    body = {"csv": report_service.to_csv, "md": report_service.to_markdown, "pdf": report_service.to_pdf}[format](report)
    media_type, ext = _EXPORTS[format]
    name = re.sub(r"[^A-Za-z0-9._-]+", "-", report["analysis"]["name"]).strip("-")[:60] or "analysis"
    return Response(content=body, media_type=media_type,
                    headers={"Content-Disposition": f'attachment; filename="{name}-report.{ext}"'})


# GET /api/v1/runs/{run_id}/diff?against=<run id>
# Example response: {"against_run_id": "...", "summary": {"improved": 2, "regressed": 0, "unchanged": 9, ...},
#                    "changes": [{"code": "REQ-013", "before": "missing", "after": "covered", "change": "improved"}, ...]}
@router.get("/runs/{run_id}/diff")
def diff_run(run_id: UUID, against: Optional[UUID] = None, db: Session = Depends(get_db)):
    """What changed per requirement compared with an earlier run (default: the previous completed run)."""
    return report_service.diff_runs(run_id, against, db)
