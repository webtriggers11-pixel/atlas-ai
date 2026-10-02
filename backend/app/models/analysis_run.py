import uuid
from sqlalchemy import Column, Text, Integer, DateTime, ForeignKey, CheckConstraint, Index, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.db.base import Base

RUN_STATUSES = ("queued", "running", "completed", "failed")


class AnalysisRun(Base):
    """One execution of the gap analysis over a project's approved requirements."""

    __tablename__ = "analysis_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    status = Column(Text, server_default="'queued'", nullable=False)
    total = Column(Integer, server_default="0", nullable=False)        # requirements to analyse
    processed = Column(Integer, server_default="0", nullable=False)    # requirements finished so far
    model = Column(Text, nullable=True)
    prompt_version = Column(Text, nullable=True)
    stats = Column(JSONB, nullable=True)            # counts per status, cache hits, llm calls, timings
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)

    project = relationship("Project", back_populates="runs")
    findings = relationship("Finding", back_populates="run", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("status IN ('queued', 'running', 'completed', 'failed')", name="ck_analysis_run_status"),
        Index("idx_analysis_runs_project_id", "project_id"),
    )
