"""
Ingestion service — upload (validate, dedupe, store, enqueue) and processing
(extract → normalize → chunk → embed → index) of project documents.

Status lifecycle:  uploaded → processing → indexed
                                       └──→ failed (error_message explains why)
"""
import hashlib
import logging
from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import ProjectDocument, DocChunk
from app.services import retrieval, storage
from app.services.chunking import chunk_pages
from app.services.extraction import DocumentError, detect_file_type, extract_pages, safe_filename
from app.services.project_service import get_project_or_404, get_document_or_404

logger = logging.getLogger(__name__)


def _enqueue(document_id: UUID, force: bool = False) -> bool:
    """Queue background processing; return False (instead of failing the upload) if the queue is down."""
    try:
        # imported here (inside the try) so a missing/broken queue setup degrades to a visible
        # message on the document instead of a 500 that leaves it stuck as "uploaded"
        from app.tasks import process_document

        process_document.delay(str(document_id), force)
        return True
    except DocumentError:
        raise
    except Exception as exc:  # broker unreachable or Celery not installed — the upload itself still succeeded
        logger.warning("Could not enqueue processing for %s: %s", document_id, exc)
        return False


def upload_document(project_id: UUID, role: str, filename: str, data: bytes, db: Session) -> tuple[ProjectDocument, bool]:
    """Validate and store an upload, then queue processing. Returns (document, created).

    Uploading the same bytes twice to a project returns the existing document
    (created=False) instead of storing and processing a duplicate.
    """
    get_project_or_404(project_id, db)
    filename = safe_filename(filename)
    try:
        file_type = detect_file_type(filename, data)
    except DocumentError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    content_hash = hashlib.sha256(data).hexdigest()
    existing = db.execute(
        select(ProjectDocument).where(
            ProjectDocument.project_id == project_id, ProjectDocument.content_hash == content_hash
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing, False

    document_id = uuid4()
    storage_path = storage.save_file(project_id, document_id, file_type, data)
    document = ProjectDocument(
        id=document_id, project_id=project_id, role=role, filename=filename[:255], file_type=file_type,
        size_bytes=len(data), content_hash=content_hash, storage_path=storage_path, status="uploaded",
    )
    db.add(document)
    db.commit()

    if not _enqueue(document.id):
        document.error_message = "Processing queue unavailable — use Reprocess to try again."
        db.commit()
    db.refresh(document)
    return document, True


def reprocess_document(document_id: UUID, db: Session) -> ProjectDocument:
    """Re-run processing for a failed/stuck document (safe to call repeatedly)."""
    document = get_document_or_404(document_id, db)
    if document.status == "processing":
        raise HTTPException(status_code=409, detail="Document is already being processed.")
    document.status = "uploaded"
    document.error_message = None
    db.commit()
    if not _enqueue(document.id, force=True):
        document.error_message = "Processing queue unavailable — use Reprocess to try again."
        db.commit()
    db.refresh(document)
    return document


def _set_status(document: ProjectDocument, status: str, db: Session, error: str | None = None) -> None:
    """Persist a status change immediately so the UI sees progress."""
    document.status = status
    document.error_message = error
    if status in ("indexed", "failed"):
        document.processed_at = datetime.now(timezone.utc)
    db.commit()


def process_document(document_id: str | UUID, db: Session, force: bool = False) -> None:
    """Process one document. Idempotent: re-running replaces its chunks instead of duplicating them."""
    document = db.get(ProjectDocument, UUID(str(document_id)))
    if document is None:
        logger.warning("process_document: %s no longer exists — skipping", document_id)
        return
    if document.status == "indexed" and not force:
        return  # already done (e.g. the task was delivered twice)

    _set_status(document, "processing", db)
    try:
        pages = extract_pages(storage.read_file(document.storage_path), document.file_type)
        chunks = chunk_pages(pages)

        # Replace, never append: a retried task must not create duplicate chunks
        db.execute(delete(DocChunk).where(DocChunk.document_id == document.id))
        rows = [
            DocChunk(
                document_id=document.id, chunk_index=c.chunk_index, content=c.content, section=c.section,
                page_start=c.page_start, page_end=c.page_end, word_count=c.word_count,
            )
            for c in chunks
        ]
        db.add_all(rows)
        db.flush()
        retrieval.embed_chunks(rows, db)

        document.chunk_count = len(rows)
        document.page_count = max((p.number for p in pages if p.number), default=None)
        _set_status(document, "indexed", db)
    except DocumentError as exc:
        db.rollback()
        _set_status(document, "failed", db, str(exc))
    except FileNotFoundError:
        db.rollback()
        _set_status(document, "failed", db, "Stored file is missing — upload the document again.")
    except Exception as exc:
        db.rollback()
        logger.exception("Unexpected error processing %s", document.id)
        _set_status(document, "failed", db, f"Internal error while processing ({type(exc).__name__}).")
        raise

