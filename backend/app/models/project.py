import uuid
from sqlalchemy import Column, Text, DateTime, CheckConstraint, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base

PROJECT_PRESETS = ("spec_coverage", "resume_jd")


class Project(Base):
    """One gap analysis: a set of reference documents compared against a set of existing documents."""

    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    preset = Column(Text, server_default="'spec_coverage'", nullable=False)
    # Owner when AUTH_ENABLED=true; NULL in single-user (no-login) mode
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    # Requirement-extraction job state: idle | running | completed | failed (validated in code;
    # our migrator only creates CHECK constraints together with a new table)
    extraction_status = Column(Text, server_default="'idle'", nullable=False)
    extraction_error = Column(Text, nullable=True)
    extracted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    documents = relationship("ProjectDocument", back_populates="project", cascade="all, delete-orphan",
                             order_by="ProjectDocument.created_at")
    requirements = relationship("Requirement", back_populates="project", cascade="all, delete-orphan",
                                order_by="Requirement.code")
    runs = relationship("AnalysisRun", back_populates="project", cascade="all, delete-orphan",
                        order_by="AnalysisRun.created_at.desc()")

    __table_args__ = (
        CheckConstraint("preset IN ('spec_coverage', 'resume_jd')", name="ck_project_preset"),
        Index("idx_projects_owner_id", "owner_id"),
    )
