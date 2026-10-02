from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.project import DocumentResponse, ChunkResponse, DocumentListItem
from app.services import project_service, ingestion_service

router = APIRouter(prefix="/documents", tags=["documents"])


# GET /api/v1/documents?search=resume
# Example response: [{"id": "...", "filename": "resume.pdf", "role": "existing", "status": "indexed",
#                     "project_id": "...", "project_name": "Resume vs Python JD", ...}]
@router.get("", response_model=list[DocumentListItem])
def list_all_documents(search: Optional[str] = None, db: Session = Depends(get_db)):
    """All documents across analyses, newest first (global Documents page)."""
    return project_service.list_all_documents(search, db)


# GET /api/v1/documents/{document_id}
# Example response: {"id": "...", "role": "existing", "filename": "sdd.docx", "status": "processing", ...}
@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(document_id: UUID, db: Session = Depends(get_db)):
    """Get one document — the UI polls this to follow processing status."""
    return project_service.get_document_or_404(document_id, db)


# GET /api/v1/documents?search=resume
# Example response: [{"id": "...", "filename": "resume.pdf", "role": "existing", "status": "indexed",
#                     "project_id": "...", "project_name": "Resume vs Python JD", ...}]
@router.get("", response_model=list[DocumentListItem])
def list_all_documents(search: Optional[str] = None, db: Session = Depends(get_db)):
    """All documents across analyses, newest first (global Documents page)."""
    return project_service.list_all_documents(search, db)


# GET /api/v1/documents/{document_id}/chunks
# Example response: [{"id": "...", "chunk_index": 0, "section": "1. Overview", "page_start": 1, "content": "..."}]
@router.get("/{document_id}/chunks", response_model=list[ChunkResponse])
def list_chunks(document_id: UUID, db: Session = Depends(get_db)):
    """List a document's chunks in reading order."""
    return project_service.list_chunks(document_id, db)


# DELETE /api/v1/documents/{document_id}
# Example response: 204 No Content
@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: UUID, db: Session = Depends(get_db)):
    """Delete a document, its chunks and its stored file."""
    project_service.delete_document(document_id, db)


# POST /api/v1/documents/{document_id}/reprocess
# Example response: 202 {"id": "...", "status": "uploaded", ...}  — processing re-queued
@router.post("/{document_id}/reprocess", response_model=DocumentResponse, status_code=status.HTTP_202_ACCEPTED)
def reprocess_document(document_id: UUID, db: Session = Depends(get_db)):
    """Re-run extraction/chunking for a failed or stuck document."""
    return ingestion_service.reprocess_document(document_id, db)
