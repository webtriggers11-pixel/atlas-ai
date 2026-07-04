import uuid
from sqlalchemy import Column, Text, DateTime, ForeignKey, UniqueConstraint, CheckConstraint, Index, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base


class NodeExplanation(Base):
    """Cached explanation for a node at a specific depth (gist / standard / expert)."""

    __tablename__ = "node_explanations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    node_id = Column(UUID(as_uuid=True), ForeignKey("nodes.id", ondelete="CASCADE"), nullable=False)
    depth = Column(Text, nullable=False)  # enforced by check constraint below
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    node = relationship("Node", back_populates="explanations")

    __table_args__ = (
        UniqueConstraint("node_id", "depth", name="uq_node_depth"),
        CheckConstraint("depth IN ('gist', 'standard', 'expert')", name="ck_depth_values"),
        # unique constraint already creates an index; name it explicitly for clarity
        Index("idx_node_explanations_node_depth", "node_id", "depth"),
    )
