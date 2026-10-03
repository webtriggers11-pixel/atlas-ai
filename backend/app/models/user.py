import uuid
from sqlalchemy import Column, Text, DateTime, Index, func
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base


class User(Base):
    """An account — only used when AUTH_ENABLED=true (hosted / multi-user mode)."""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(Text, nullable=False)                 # stored lower-cased
    password_hash = Column(Text, nullable=False)         # bcrypt — never the password itself
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("uq_users_email", "email", unique=True),
    )
