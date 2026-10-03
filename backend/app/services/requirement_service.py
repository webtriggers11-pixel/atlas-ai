"""
Requirement service — the reviewable list of requirements (REQ-001 ...) for a project.
"""
import hashlib
import re
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import ensure_owner
from app.models import Requirement
from app.schemas.project import RequirementCreate, RequirementUpdate
from app.services.project_service import get_project_or_404


def requirement_hash(text: str) -> str:
    """sha256 of the requirement text, lower-cased with whitespace collapsed, so cosmetic edits don't change it."""
    normalized = re.sub(r"\s+", " ", text).strip().lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def next_codes(project_id: UUID, count: int, db: Session) -> list[str]:
    """Return the next `count` unused codes for a project, e.g. ['REQ-007', 'REQ-008']."""
    codes = db.execute(select(Requirement.code).where(Requirement.project_id == project_id)).scalars().all()
    numbers = [int(m.group(1)) for c in codes if (m := re.fullmatch(r"REQ-(\d+)", c))]
    start = max(numbers, default=0) + 1
    return [f"REQ-{n:03d}" for n in range(start, start + count)]


def get_requirement_or_404(requirement_id: UUID, db: Session) -> Requirement:
    """Fetch a requirement by id or raise 404."""
    requirement = db.get(Requirement, requirement_id)
    if requirement is None:
        raise HTTPException(status_code=404, detail=f"Requirement {requirement_id} not found.")
    ensure_owner(requirement.project.owner_id)
    return requirement


def list_requirements(project_id: UUID, status: str | None, db: Session) -> list[Requirement]:
    """Return a project's requirements in code order, optionally filtered by status."""
    get_project_or_404(project_id, db)
    query = select(Requirement).where(Requirement.project_id == project_id)
    if status:
        query = query.where(Requirement.status == status)
    return db.execute(query.order_by(Requirement.code)).scalars().all()


def create_requirement(project_id: UUID, body: RequirementCreate, db: Session) -> Requirement:
    """Add a requirement typed by the user; it starts approved because a human wrote it."""
    get_project_or_404(project_id, db)
    requirement = Requirement(
        project_id=project_id,
        code=next_codes(project_id, 1, db)[0],
        text=body.text,
        section=body.section,
        status="approved",
        origin="manual",
        content_hash=requirement_hash(body.text),
    )
    db.add(requirement)
    db.commit()
    db.refresh(requirement)
    return requirement


def update_requirement(requirement_id: UUID, body: RequirementUpdate, db: Session) -> Requirement:
    """Edit text/section/status of a requirement (the review step)."""
    requirement = get_requirement_or_404(requirement_id, db)
    if body.text is not None:
        requirement.text = body.text
        requirement.content_hash = requirement_hash(body.text)
    if body.section is not None:
        requirement.section = body.section or None
    if body.status is not None:
        requirement.status = body.status
    db.commit()
    db.refresh(requirement)
    return requirement


def approve_all(project_id: UUID, db: Session) -> int:
    """Approve every draft requirement in a project; return how many changed."""
    drafts = list_requirements(project_id, "draft", db)
    for requirement in drafts:
        requirement.status = "approved"
    db.commit()
    return len(drafts)


def merge_requirements(project_id: UUID, ids: list[UUID], text: str | None, db: Session) -> Requirement:
    """Merge several requirements into the first one: combine text, reject the others."""
    if len(ids) < 2:
        raise HTTPException(status_code=422, detail="Select at least two requirements to merge.")
    requirements = [get_requirement_or_404(i, db) for i in ids]
    if any(r.project_id != project_id for r in requirements):
        raise HTTPException(status_code=422, detail="All requirements must belong to this project.")

    keep, *others = requirements
    merged_text = (text or " ".join(r.text for r in requirements)).strip()
    keep.text = merged_text
    keep.content_hash = requirement_hash(merged_text)
    keep.status = "approved"
    for other in others:
        other.status = "rejected"
    db.commit()
    db.refresh(keep)
    return keep
