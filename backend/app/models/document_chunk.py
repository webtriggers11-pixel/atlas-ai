import uuid
from sqlalchemy import Column, Text, Integer, DateTime, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.db.base import Base


class DocumentChunk(Base):
    """One ~500-word slice of a document with its embedding vector for similarity search."""

    __tablename__ = "document_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    # 384-dim MiniLM embedding stored as a JSON float array; cosine similarity is
    # computed in Python — fine at single-user scale, no pgvector extension needed
    embedding = Column(JSONB, nullable=True)
    section_hint = Column(Text, nullable=True)  # nearest heading found above this chunk
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    document = relationship("Document", back_populates="chunks")

    __table_args__ = (
        Index("idx_document_chunks_document_id", "document_id"),
    )
