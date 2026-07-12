import uuid
from sqlalchemy import Column, Text, DateTime, ForeignKey, CheckConstraint, Index, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base


class Document(Base):
    """An uploaded or pasted source document that a map can be grounded in."""

    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    map_id = Column(UUID(as_uuid=True), ForeignKey("maps.id", ondelete="SET NULL"), nullable=True)
    filename = Column(Text, nullable=False)
    source_type = Column(Text, nullable=False)  # enforced by check constraint below
    full_text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    chunks = relationship(
        "DocumentChunk",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentChunk.chunk_index",
    )

    __table_args__ = (
        CheckConstraint("source_type IN ('docx', 'pdf', 'pasted')", name="ck_document_source_type"),
        Index("idx_documents_map_id", "map_id"),
    )
