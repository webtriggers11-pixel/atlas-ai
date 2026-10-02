import uuid
from sqlalchemy import Column, Text, Integer, DateTime, Index, func
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base


class LlmCall(Base):
    """One provider attempt (V2): who served it, how long it took, how many tokens, and why it failed if it did.

    A new table rather than new columns on v1's llm_logs, so the live v1 app's migrator
    can never drop these columns.
    """

    __tablename__ = "llm_calls"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider = Column(Text, nullable=False)          # groq | gemini | ollama
    model = Column(Text, nullable=True)
    task_type = Column(Text, nullable=False)         # classify_requirements | extract_requirements | ...
    prompt_version = Column(Text, nullable=True)
    status = Column(Text, nullable=False)            # ok | ok_after_retry | rate_limited | unavailable
    attempt = Column(Integer, server_default="1", nullable=False)
    latency_ms = Column(Integer, nullable=False)
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    context = Column(Text, nullable=True)            # e.g. "run:<uuid>" — which job made the call
    error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_llm_calls_context", "context"),
        Index("idx_llm_calls_created_at", "created_at"),
    )
