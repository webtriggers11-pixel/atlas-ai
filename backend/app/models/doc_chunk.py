import uuid
from sqlalchemy import Column, Text, Integer, DateTime, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base


class DocChunk(Base):
    """One slice of a project document, with section and page location so evidence can be cited."""

    __tablename__ = "doc_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("project_documents.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    section = Column(Text, nullable=True)       # nearest heading above the chunk
    page_start = Column(Integer, nullable=True)
    page_end = Column(Integer, nullable=True)
    word_count = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    document = relationship("ProjectDocument", back_populates="chunks")

    __table_args__ = (
        Index("uq_doc_chunks_document_index", "document_id", "chunk_index", unique=True),
    )
