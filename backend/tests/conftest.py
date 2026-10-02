"""
Shared pytest setup.

Safety first: every test runs against a *test* database, never the real one.
- TEST_DATABASE_URL (env or backend/.env) is used if set; otherwise the
  DATABASE_URL from .env with the database name replaced by "<name>-test".
- The run aborts unless the database name ends in "-test" or "_test".

The env vars are set BEFORE `app` is imported, because app.core.config reads
settings once at import time (pydantic-settings: env vars beat .env values).
"""
import os
import tempfile
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy.engine import make_url

_ENV = dotenv_values(Path(__file__).parents[1] / ".env")


def _test_database_url() -> str:
    """Resolve the test DB URL and refuse anything that does not look like a test database."""
    explicit = os.getenv("TEST_DATABASE_URL") or _ENV.get("TEST_DATABASE_URL")
    if explicit:
        url = make_url(explicit)
    else:
        base = os.getenv("DATABASE_URL") or _ENV.get("DATABASE_URL")
        if not base:
            raise RuntimeError("Set TEST_DATABASE_URL (or DATABASE_URL) to run the tests.")
        url = make_url(base)
        if not url.database.endswith(("-test", "_test")):
            url = url.set(database=f"{url.database}-test")
    if not url.database.endswith(("-test", "_test")):
        raise RuntimeError(f"Refusing to run tests against non-test database {url.database!r}.")
    return url.render_as_string(hide_password=False)


os.environ["DATABASE_URL"] = _test_database_url()
os.environ["AUTO_MIGRATE"] = "false"
os.environ["UPLOAD_DIR"] = tempfile.mkdtemp(prefix="atlas-test-uploads-")
os.environ["EMBEDDING_PROVIDER"] = "fake"        # deterministic vectors, no model download
os.environ["CELERY_TASK_ALWAYS_EAGER"] = "true"  # background tasks run inline during tests
os.environ["RATE_LIMIT_ENABLED"] = "false"

import pytest  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.exc import OperationalError  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402


@pytest.fixture(scope="session")
def test_engine():
    """Engine for the test database; skips DB tests if it is unreachable."""
    engine = create_engine(os.environ["DATABASE_URL"], connect_args={"connect_timeout": 10})
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except OperationalError as exc:
        pytest.skip(f"Test database unreachable: {exc.orig}")
    return engine


@pytest.fixture(scope="session")
def migrated(test_engine, tmp_path_factory):
    """Bring the test database schema up to date using OUR migration system (also tests the migrator)."""
    from app.db.base import Base
    import app.models  # noqa: F401
    from migrations.migration_manager import MigrationManager

    # Generated .sql files go to a temp dir so they never mix with real migration files
    manager = MigrationManager(
        os.environ["DATABASE_URL"], Base.metadata,
        migrations_dir=str(tmp_path_factory.mktemp("migrations")),
    )
    manager.generate_migration()
    manager.apply_migrations()
    return test_engine


@pytest.fixture
def db(migrated):
    """A session whose work is rolled back after each test, even if the code under test calls commit()."""
    from app.main import app
    from app.db import get_db

    connection = migrated.connect()
    outer = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    app.dependency_overrides[get_db] = lambda: session
    try:
        yield session
    finally:
        session.close()
        outer.rollback()
        connection.close()
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def client(db):
    """FastAPI TestClient wired to the rolled-back test session."""
    from fastapi.testclient import TestClient
    from app.main import app

    return TestClient(app)
