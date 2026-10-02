from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Server-side safety nets: a session left "idle in transaction" by a crashed/killed client
# would otherwise hold its locks until TCP notices (hours) and block migrations and writers.
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    connect_args={
        "options": "-c idle_in_transaction_session_timeout=600000",   # 10 min, in ms
        "keepalives": 1, "keepalives_idle": 60, "keepalives_interval": 10, "keepalives_count": 3,
    },
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """FastAPI dependency — yields a DB session and closes it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
