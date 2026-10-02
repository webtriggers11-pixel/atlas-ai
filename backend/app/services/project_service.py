"""
Project service — create/list/rename/delete projects and read their documents.
Routers call these functions; they never touch HTTP request objects.
"""
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Project, ProjectDocument, Requirement, AnalysisRun, DocChunk
from app.schemas.project import ProjectCreate, ProjectResponse


def get_project_or_404(project_id: UUID, db: Session) -> Project:
    """Fetch a project by id or raise 404."""
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found.")
    return project


def _to_response(project: Project, db: Session) -> ProjectResponse:
    """Build a ProjectResponse with document/requirement counts and the latest run status."""
    doc_counts = dict(
        db.execute(
            select(ProjectDocument.role, func.count())
            .where(ProjectDocument.project_id == project.id)
            .group_by(ProjectDocument.role)
        ).all()
    )
    req_counts = dict(
        db.execute(
            select(Requirement.status, func.count())
            .where(Requirement.project_id == project.id)
            .group_by(Requirement.status)
        ).all()
    )
    latest_run_status = db.execute(
        select(AnalysisRun.status)
        .where(AnalysisRun.project_id == project.id)
        .order_by(AnalysisRun.created_at.desc())
        .limit(1)
    ).scalar()
    return ProjectResponse(
        id=project.id,
        name=project.name,
        preset=project.preset,
        created_at=project.created_at,
        updated_at=project.updated_at,
        reference_documents=doc_counts.get("reference", 0),
        existing_documents=doc_counts.get("existing", 0),
        requirements=sum(n for status, n in req_counts.items() if status != "rejected"),
        approved_requirements=req_counts.get("approved", 0),
        latest_run_status=latest_run_status,
    )


def create_project(body: ProjectCreate, db: Session) -> ProjectResponse:
    """Insert a new project and return it."""
    project = Project(name=body.name, preset=body.preset)
    db.add(project)
    db.commit()
    db.refresh(project)
    return _to_response(project, db)


def list_projects(db: Session) -> list[ProjectResponse]:
    """Return all projects, most recently updated first."""
    projects = db.execute(select(Project).order_by(Project.updated_at.desc())).scalars().all()
    return [_to_response(p, db) for p in projects]


def get_project(project_id: UUID, db: Session) -> ProjectResponse:
    """Return one project with its counts."""
    return _to_response(get_project_or_404(project_id, db), db)


def rename_project(project_id: UUID, name: str, db: Session) -> ProjectResponse:
    """Change a project's name."""
    project = get_project_or_404(project_id, db)
    project.name = name
    db.commit()
    db.refresh(project)
    return _to_response(project, db)


def delete_project(project_id: UUID, db: Session) -> None:
    """Delete a project, its rows (via FK cascade) and its stored files."""
    from app.services import storage

    project = get_project_or_404(project_id, db)
    paths = [d.storage_path for d in project.documents]
    db.delete(project)
    db.commit()
    for path in paths:
        storage.delete_file(path)


# ── Documents (read/delete; upload lives in ingestion_service) ───────────────

def list_documents(project_id: UUID, role: str | None, db: Session) -> list[ProjectDocument]:
    """Return a project's documents, optionally filtered by role."""
    get_project_or_404(project_id, db)
    query = select(ProjectDocument).where(ProjectDocument.project_id == project_id)
    if role:
        query = query.where(ProjectDocument.role == role)
    return db.execute(query.order_by(ProjectDocument.created_at)).scalars().all()


def get_document_or_404(document_id: UUID, db: Session) -> ProjectDocument:
    """Fetch a project document by id or raise 404."""
    document = db.get(ProjectDocument, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found.")
    return document


def list_chunks(document_id: UUID, db: Session) -> list[DocChunk]:
    """Return a document's chunks in reading order."""
    get_document_or_404(document_id, db)
    return db.execute(
        select(DocChunk).where(DocChunk.document_id == document_id).order_by(DocChunk.chunk_index)
    ).scalars().all()


def delete_document(document_id: UUID, db: Session) -> None:
    """Delete a document, its chunks (FK cascade) and its stored file."""
    from app.services import storage

    document = get_document_or_404(document_id, db)
    path = document.storage_path
    db.delete(document)
    db.commit()
    storage.delete_file(path)
