import uuid
from sqlalchemy import Column, Text, Integer, DateTime, ForeignKey, CheckConstraint, Index, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base

DOCUMENT_ROLES = ("reference", "existing")
DOCUMENT_STATUSES = ("uploaded", "processing", "indexed", "failed")


class ProjectDocument(Base):
    """A file uploaded into a project, either as a reference (expected) or existing (actual) document."""

    __tablename__ = "project_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    role = Column(Text, nullable=False)                 # reference | existing
    filename = Column(Text, nullable=False)             # original name, display only — never used in paths
    file_type = Column(Text, nullable=False)            # pdf | docx | txt | md
    size_bytes = Column(Integer, nullable=False)
    content_hash = Column(Text, nullable=False)         # sha256 of the raw bytes — dedupe + idempotency
    storage_path = Column(Text, nullable=False)         # relative to UPLOAD_DIR
    status = Column(Text, server_default="'uploaded'", nullable=False)
    error_message = Column(Text, nullable=True)
    page_count = Column(Integer, nullable=True)
    chunk_count = Column(Integer, server_default="0", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)

    project = relationship("Project", back_populates="documents")
    chunks = relationship("DocChunk", back_populates="document", cascade="all, delete-orphan",
                          order_by="DocChunk.chunk_index")

    __table_args__ = (
        CheckConstraint("role IN ('reference', 'existing')", name="ck_project_document_role"),
        CheckConstraint("file_type IN ('pdf', 'docx', 'txt', 'md')", name="ck_project_document_file_type"),
        CheckConstraint("status IN ('uploaded', 'processing', 'indexed', 'failed')", name="ck_project_document_status"),
        Index("idx_project_documents_project_id", "project_id"),
        Index("uq_project_documents_project_hash", "project_id", "content_hash", unique=True),
    )
