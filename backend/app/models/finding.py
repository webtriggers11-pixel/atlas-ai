import uuid
from sqlalchemy import Column, Text, Float, DateTime, ForeignKey, CheckConstraint, Index, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base

FINDING_STATUSES = ("covered", "partial", "missing", "conflict", "unclear")


class Finding(Base):
    """The analysis verdict for one requirement in one run, backed by evidence rows."""

    __tablename__ = "findings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False)
    requirement_id = Column(UUID(as_uuid=True), ForeignKey("requirements.id", ondelete="CASCADE"), nullable=False)
    status = Column(Text, nullable=False)
    confidence = Column(Float, nullable=True)
    explanation = Column(Text, nullable=False)
    missing_detail = Column(Text, nullable=True)      # what part of the requirement has no evidence
    suggested_action = Column(Text, nullable=True)
    source = Column(Text, server_default="'pipeline'", nullable=False)   # pipeline | agent | cache
    cache_key = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    run = relationship("AnalysisRun", back_populates="findings")
    requirement = relationship("Requirement")
    evidence = relationship("Evidence", back_populates="finding", cascade="all, delete-orphan",
                            order_by="Evidence.score.desc()")

    __table_args__ = (
        CheckConstraint("status IN ('covered', 'partial', 'missing', 'conflict', 'unclear')", name="ck_finding_status"),
        CheckConstraint("source IN ('pipeline', 'agent', 'cache')", name="ck_finding_source"),
        Index("uq_findings_run_requirement", "run_id", "requirement_id", unique=True),
        Index("idx_findings_cache_key", "cache_key"),
    )
