import uuid
from sqlalchemy import Column, Text, Float, Boolean, DateTime, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base


class Evidence(Base):
    """A quote from a document chunk that supports (or contradicts) a finding."""

    __tablename__ = "evidence"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    finding_id = Column(UUID(as_uuid=True), ForeignKey("findings.id", ondelete="CASCADE"), nullable=False)
    chunk_id = Column(UUID(as_uuid=True), ForeignKey("doc_chunks.id", ondelete="CASCADE"), nullable=False)
    quote = Column(Text, nullable=False)
    verified = Column(Boolean, server_default="false", nullable=False)   # quote really appears in the chunk
    score = Column(Float, nullable=True)                                 # retrieval relevance
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    finding = relationship("Finding", back_populates="evidence")
    chunk = relationship("DocChunk")

    __table_args__ = (
        Index("idx_evidence_finding_id", "finding_id"),
    )
