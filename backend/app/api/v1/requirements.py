from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.project import RequirementUpdate, RequirementResponse
from app.services import requirement_service

router = APIRouter(prefix="/requirements", tags=["requirements"])


# PATCH /api/v1/requirements/{requirement_id}
# Example request:  {"text": "Access tokens expire after 15 minutes.", "status": "approved"}
# Example response: {"id": "...", "code": "REQ-004", "text": "Access tokens expire after 15 minutes.", "status": "approved", ...}
@router.patch("/{requirement_id}", response_model=RequirementResponse)
def update_requirement(requirement_id: UUID, body: RequirementUpdate, db: Session = Depends(get_db)):
    """Edit, approve or reject a requirement during review."""
    return requirement_service.update_requirement(requirement_id, body, db)
