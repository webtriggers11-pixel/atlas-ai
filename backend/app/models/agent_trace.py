import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, Text, Integer, Float, DateTime, ForeignKey, CheckConstraint, Index, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.db.base import Base


class AgentTrace(Base):
    """One investigator-agent run on one finding: every tool call it made and what it concluded."""

    __tablename__ = "agent_traces"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    finding_id = Column(UUID(as_uuid=True), ForeignKey("findings.id", ondelete="CASCADE"), nullable=False)
    status = Column(Text, server_default="'queued'", nullable=False)      # queued | running | completed | failed
    previous_status = Column(Text, nullable=False)                      # finding status before investigation
    new_status = Column(Text, nullable=True)                            # the agent's verdict (if any)
    # changed = finding updated · confirmed = same verdict · rejected = verdict failed verification
    # kept = agent claimed missing/unclear (unverifiable) — recorded, not applied
    # no_verdict = budget ran out without a verdict · error = the run crashed
    outcome = Column(Text, nullable=True)
    explanation = Column(Text, nullable=True)
    steps = Column(JSONB, nullable=True)                                # [{tool, arguments, ok, summary}]
    tool_calls = Column(Integer, server_default="0", nullable=False)
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    duration_s = Column(Float, nullable=True)
    error = Column(Text, nullable=True)
    # Python clock, not SQL now(): now() is the transaction start, so traces created in one
    # transaction would tie and "newest first" ordering would be ambiguous.
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        server_default=func.now(), nullable=False)
    finished_at = Column(DateTime(timezone=True), nullable=True)

    finding = relationship("Finding", back_populates="traces")

    __table_args__ = (
        CheckConstraint("status IN ('queued', 'running', 'completed', 'failed')", name="ck_agent_trace_status"),
        Index("idx_agent_traces_finding_id", "finding_id"),
    )
