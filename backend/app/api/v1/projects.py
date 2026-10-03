from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.project import (
    ProjectCreate, ProjectUpdate, ProjectResponse, DocumentResponse, DocumentRole,
    RequirementCreate, RequirementResponse, RequirementStatus, RequirementMerge, ApproveAllResponse,
    RunResponse, SearchRequest, SearchResult, ChatRequest, ChatResponse,
)
from app.core.config import settings
from app.services import project_service, requirement_service, findings_service, ingestion_service, retrieval, extraction_job, analysis_service, chat_service

router = APIRouter(prefix="/projects", tags=["projects"])


# POST /api/v1/projects
# Example request:  {"name": "Payments API v2 review", "preset": "spec_coverage"}
# Example response: {"id": "...", "name": "Payments API v2 review", "preset": "spec_coverage",
#                    "reference_documents": 0, "existing_documents": 0, "requirements": 0, ...}
@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(body: ProjectCreate, db: Session = Depends(get_db)):
    """Create a new analysis project."""
    return project_service.create_project(body, db)


# GET /api/v1/projects
# Example response: [{"id": "...", "name": "Payments API v2 review", "latest_run_status": "completed", ...}]
@router.get("", response_model=list[ProjectResponse])
def list_projects(db: Session = Depends(get_db)):
    """List all projects, most recently updated first."""
    return project_service.list_projects(db)


# GET /api/v1/projects/{project_id}
# Example response: {"id": "...", "name": "...", "reference_documents": 1, "existing_documents": 2, ...}
@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: UUID, db: Session = Depends(get_db)):
    """Get one project with document and requirement counts."""
    return project_service.get_project(project_id, db)


# PATCH /api/v1/projects/{project_id}
# Example request:  {"name": "Payments API v2 — final review"}
# Example response: the updated project
@router.patch("/{project_id}", response_model=ProjectResponse)
def rename_project(project_id: UUID, body: ProjectUpdate, db: Session = Depends(get_db)):
    """Rename a project."""
    return project_service.rename_project(project_id, body.name, db)


# DELETE /api/v1/projects/{project_id}
# Example response: 204 No Content
@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: UUID, db: Session = Depends(get_db)):
    """Delete a project with all its documents, requirements, runs and stored files."""
    project_service.delete_project(project_id, db)


# GET /api/v1/projects/{project_id}/documents?role=reference
# Example response: [{"id": "...", "role": "reference", "filename": "srs.pdf", "status": "indexed", ...}]
@router.get("/{project_id}/documents", response_model=list[DocumentResponse])
def list_documents(project_id: UUID, role: Optional[DocumentRole] = None, db: Session = Depends(get_db)):
    """List a project's documents, optionally only one role."""
    return project_service.list_documents(project_id, role, db)


# POST /api/v1/projects/{project_id}/documents   (multipart/form-data)
# Example request:  role=reference, file=@srs.pdf          — or —   role=existing, text="pasted...", title="notes"
# Example response: 201 {"id": "...", "role": "reference", "filename": "srs.pdf", "status": "uploaded", ...}
#                   200 with the existing document if the same file was already uploaded to this project
@router.post("/{project_id}/documents", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def upload_document(
    project_id: UUID,
    response: Response,
    role: DocumentRole = Form(...),
    file: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None),
    title: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """Upload a file (or pasted text) as a reference/existing document; processing runs in the background."""
    limit = settings.MAX_UPLOAD_MB * 1024 * 1024
    if file is not None and file.filename:
        data = file.file.read(limit + 1)   # read at most limit+1 bytes so a huge upload can't exhaust memory
        filename = file.filename
    elif text and text.strip():
        data = text.encode("utf-8")
        filename = f"{(title or 'pasted-text').strip()[:100]}.txt"
    else:
        raise HTTPException(status_code=422, detail="Send a file or non-empty text.")
    if len(data) > limit:
        raise HTTPException(status_code=413, detail=f"File is larger than the {settings.MAX_UPLOAD_MB} MB limit.")

    document, created = ingestion_service.upload_document(project_id, role, filename, data, db)
    if not created:
        response.status_code = status.HTTP_200_OK
    return document


# GET /api/v1/projects/{project_id}/requirements?status=draft
# Example response: [{"id": "...", "code": "REQ-001", "text": "The system must ...", "status": "draft", ...}]
@router.get("/{project_id}/requirements", response_model=list[RequirementResponse])
def list_requirements(project_id: UUID, status: Optional[RequirementStatus] = None, db: Session = Depends(get_db)):
    """List a project's requirements in code order."""
    return requirement_service.list_requirements(project_id, status, db)


# POST /api/v1/projects/{project_id}/requirements
# Example request:  {"text": "Refresh tokens must expire after 30 days.", "section": "Authentication"}
# Example response: {"id": "...", "code": "REQ-015", "status": "approved", "origin": "manual", ...}
@router.post("/{project_id}/requirements", response_model=RequirementResponse, status_code=status.HTTP_201_CREATED)
def create_requirement(project_id: UUID, body: RequirementCreate, db: Session = Depends(get_db)):
    """Add a requirement by hand during review."""
    return requirement_service.create_requirement(project_id, body, db)


# POST /api/v1/projects/{project_id}/requirements/extract
# Example response: 202 {"id": "...", "extraction_status": "running", ...}
#   → poll GET /api/v1/projects/{id} until extraction_status is "completed" or "failed",
#     then GET /api/v1/projects/{id}/requirements?status=draft to review
@router.post("/{project_id}/requirements/extract", response_model=ProjectResponse, status_code=status.HTTP_202_ACCEPTED)
def extract_requirements(project_id: UUID, db: Session = Depends(get_db)):
    """Start AI extraction of draft requirements from the indexed reference documents."""
    extraction_job.start_extraction(project_id, db)
    return project_service.get_project(project_id, db)


# POST /api/v1/projects/{project_id}/requirements/approve-all
# Example response: {"approved": 12}
@router.post("/{project_id}/requirements/approve-all", response_model=ApproveAllResponse)
def approve_all_requirements(project_id: UUID, db: Session = Depends(get_db)):
    """Approve every draft requirement in one click."""
    return ApproveAllResponse(approved=requirement_service.approve_all(project_id, db))


# POST /api/v1/projects/{project_id}/requirements/merge
# Example request:  {"ids": ["<REQ-003 id>", "<REQ-004 id>"], "text": "optional combined wording"}
# Example response: the kept requirement (the others become "rejected")
@router.post("/{project_id}/requirements/merge", response_model=RequirementResponse)
def merge_requirements(project_id: UUID, body: RequirementMerge, db: Session = Depends(get_db)):
    """Merge requirements the extractor split too finely."""
    return requirement_service.merge_requirements(project_id, body.ids, body.text, db)


# POST /api/v1/projects/{project_id}/analyze
# Example response: 202 {"id": "<run id>", "status": "queued", "total": 24, "processed": 0, ...}
#   → poll GET /api/v1/runs/{run_id} for progress, then GET /api/v1/runs/{run_id}/findings
@router.post("/{project_id}/analyze", response_model=RunResponse, status_code=status.HTTP_202_ACCEPTED)
def analyze(project_id: UUID, db: Session = Depends(get_db)):
    """Start a gap analysis of all approved requirements against the existing documents."""
    return analysis_service.start_analysis(project_id, db)


# GET /api/v1/projects/{project_id}/runs
# Example response: [{"id": "...", "status": "completed", "total": 24, "processed": 24, ...}]
@router.get("/{project_id}/runs", response_model=list[RunResponse])
def list_runs(project_id: UUID, db: Session = Depends(get_db)):
    """List a project's analysis runs, newest first."""
    return findings_service.list_runs(project_id, db)


# POST /api/v1/projects/{project_id}/search
# Example request:  {"query": "refresh token expiry", "role": "existing", "k": 5, "mode": "hybrid"}
# Example response: [{"chunk_id": "...", "document_filename": "sdd.pdf", "section": "4. Auth",
#                     "page_start": 7, "content": "...", "score": 0.71, "rank": 1}]
@router.post("/{project_id}/search", response_model=list[SearchResult])
def search(project_id: UUID, body: SearchRequest, db: Session = Depends(get_db)):
    """Semantic search over a project's indexed documents (also used to debug retrieval quality)."""
    project_service.get_project_or_404(project_id, db)
    results = retrieval.search(project_id, body.query, db, role=body.role, k=body.k, mode=body.mode)
    return [
        SearchResult(
            chunk_id=r.chunk.id, document_id=r.document.id, document_filename=r.document.filename,
            document_role=r.document.role, section=r.chunk.section, page_start=r.chunk.page_start,
            content=r.chunk.content, score=round(r.score, 4), rank=r.rank,
        )
        for r in results
    ]


# POST /api/v1/projects/{project_id}/chat
# Example request:  {"message": "Which security requirements are missing?", "history": []}
# Example response: {"answer": "Two are missing: [REQ-010] ... (sdd.pdf, \"5. Security\")",
#                    "steps": [{"tool": "list_findings", "arguments": {"status": "missing"}, "ok": true, "summary": "3 result(s)"}],
#                    "sources": [{"kind": "requirement", "id": "REQ-010", "status": "missing"}], ...}
@router.post("/{project_id}/chat", response_model=ChatResponse)
def chat(project_id: UUID, body: ChatRequest, db: Session = Depends(get_db)):
    """Ask a question about this analysis; the AI answers using read-only, analysis-scoped tools."""
    return chat_service.ask(project_id, body.message, [t.model_dump() for t in body.history], db)
