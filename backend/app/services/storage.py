"""
File storage for uploaded documents — local disk under settings.UPLOAD_DIR.

Paths are built only from server-generated ids (never from the user's filename),
so a malicious name like '../../etc/passwd' cannot escape the upload directory.
"""
from pathlib import Path
from uuid import UUID

from app.core.config import settings


def _root() -> Path:
    """Return the absolute upload directory, creating it if needed."""
    root = Path(settings.UPLOAD_DIR).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _resolve(relative_path: str) -> Path:
    """Turn a stored relative path into an absolute one, refusing anything outside the upload root."""
    root = _root()
    full = (root / relative_path).resolve()
    if root not in full.parents:
        raise ValueError(f"Refusing path outside upload directory: {relative_path!r}")
    return full


def save_file(project_id: UUID, document_id: UUID, file_type: str, data: bytes) -> str:
    """Write bytes to <project_id>/<document_id>.<ext> and return that relative path."""
    relative = f"{project_id}/{document_id}.{file_type}"
    full = _resolve(relative)
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_bytes(data)
    return relative


def read_file(relative_path: str) -> bytes:
    """Read a stored file's bytes."""
    return _resolve(relative_path).read_bytes()


def delete_file(relative_path: str) -> None:
    """Delete a stored file if it exists; missing files are ignored (delete is idempotent)."""
    try:
        _resolve(relative_path).unlink(missing_ok=True)
    except ValueError:
        pass
