from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.project import (
    ProjectCreate, ProjectUpdate, ProjectResponse, DocumentResponse, DocumentRole,
    RequirementCreate, RequirementResponse, RequirementStatus, RequirementMerge, ApproveAllResponse,
    RunResponse,
)
from app.services import project_service, requirement_service, findings_service

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


# GET /api/v1/projects/{project_id}/runs
# Example response: [{"id": "...", "status": "completed", "total": 24, "processed": 24, ...}]
@router.get("/{project_id}/runs", response_model=list[RunResponse])
def list_runs(project_id: UUID, db: Session = Depends(get_db)):
    """List a project's analysis runs, newest first."""
    return findings_service.list_runs(project_id, db)
