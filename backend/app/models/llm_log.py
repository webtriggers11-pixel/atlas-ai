import uuid
from sqlalchemy import Column, Text, Integer, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base


class LlmLog(Base):
    """One row per LLM request — records which provider actually served it and how long it took."""

    __tablename__ = "llm_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider = Column(Text, nullable=False)     # groq | gemini | ollama
    task_type = Column(Text, nullable=False)    # map_generation | expand_small | gist | ...
    status = Column(Text, nullable=False)       # ok | ok_after_fallback | rate_limited
    latency_ms = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
