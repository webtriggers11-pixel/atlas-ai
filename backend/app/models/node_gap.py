import uuid
from sqlalchemy import Column, Text, DateTime, ForeignKey, CheckConstraint, Index, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base


class NodeGap(Base):
    """A developer question the document doesn't answer for a given node — the gap-check output."""

    __tablename__ = "node_gaps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    node_id = Column(UUID(as_uuid=True), ForeignKey("nodes.id", ondelete="CASCADE"), nullable=False)
    question = Column(Text, nullable=False)
    status = Column(Text, server_default="'open'", nullable=False)  # open | answered
    answer = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    node = relationship("Node", back_populates="gaps")

    __table_args__ = (
        CheckConstraint("status IN ('open', 'answered')", name="ck_node_gap_status"),
        Index("idx_node_gaps_node_id", "node_id"),
    )
