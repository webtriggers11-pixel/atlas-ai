"""
Celery tasks. Each task only receives ids (never ORM objects), opens its own DB
session, and delegates to a service function that is safe to run more than once.
"""
import logging
from contextlib import contextmanager

from sqlalchemy.exc import OperationalError

from app.worker import celery_app

logger = logging.getLogger(__name__)


@contextmanager
def session_scope():
    """Yield a fresh DB session for one task and always close it (tests replace this with the test session)."""
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Transient infrastructure errors are retried with backoff; document errors are not (see the service).
_RETRY = dict(autoretry_for=(OperationalError,), retry_backoff=5, retry_backoff_max=60, max_retries=3)


@celery_app.task(name="atlas.process_document", **_RETRY)
def process_document(document_id: str, force: bool = False) -> None:
    """Extract → normalize → chunk → embed → index one uploaded document."""
    from app.services import ingestion_service

    with session_scope() as db:
        ingestion_service.process_document(document_id, db, force=force)


@celery_app.task(name="atlas.extract_requirements", **_RETRY)
def extract_requirements(project_id: str) -> None:
    """Extract draft requirements from a project's indexed reference documents."""
    from app.services import extraction_job

    with session_scope() as db:
        extraction_job.run_extraction(project_id, db)
