import uuid
from sqlalchemy import Column, Text, Boolean, Float, DateTime, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base


class Node(Base):
    """A single concept on a map — either the root topic or a sub-concept."""

    __tablename__ = "nodes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    map_id = Column(UUID(as_uuid=True), ForeignKey("maps.id", ondelete="CASCADE"), nullable=False)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("nodes.id", ondelete="SET NULL"), nullable=True)
    label = Column(Text, nullable=False)
    position_x = Column(Float, nullable=True)
    position_y = Column(Float, nullable=True)
    is_root = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    map = relationship("Map", back_populates="nodes")
    # self-referential: parent node → children nodes
    parent = relationship("Node", remote_side="Node.id", back_populates="children")
    children = relationship("Node", back_populates="parent")
    explanations = relationship("NodeExplanation", back_populates="node", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_nodes_map_id", "map_id"),
        Index("idx_nodes_parent_id", "parent_id"),
    )
