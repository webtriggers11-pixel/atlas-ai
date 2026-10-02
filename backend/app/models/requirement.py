import uuid
from sqlalchemy import Column, Text, DateTime, ForeignKey, CheckConstraint, Index, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base

REQUIREMENT_STATUSES = ("draft", "approved", "rejected")


class Requirement(Base):
    """One requirement/claim from the reference documents, e.g. REQ-014. Reviewed by the user before analysis."""

    __tablename__ = "requirements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    code = Column(Text, nullable=False)                 # REQ-001, stable per project
    text = Column(Text, nullable=False)
    section = Column(Text, nullable=True)
    status = Column(Text, server_default="'draft'", nullable=False)
    origin = Column(Text, server_default="'extracted'", nullable=False)   # extracted | manual
    source_chunk_id = Column(UUID(as_uuid=True), ForeignKey("doc_chunks.id", ondelete="SET NULL"), nullable=True)
    content_hash = Column(Text, nullable=False)         # sha256 of normalized text — analysis cache key input
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    project = relationship("Project", back_populates="requirements")
    source_chunk = relationship("DocChunk")

    __table_args__ = (
        CheckConstraint("status IN ('draft', 'approved', 'rejected')", name="ck_requirement_status"),
        CheckConstraint("origin IN ('extracted', 'manual')", name="ck_requirement_origin"),
        Index("uq_requirements_project_code", "project_id", "code", unique=True),
    )
