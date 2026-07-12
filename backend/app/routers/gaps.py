from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import AnswerGapRequest, GapQuestionResponse
from app.services import document_service

router = APIRouter(prefix="/gaps", tags=["gaps"])


# PATCH /gaps/{gap_id}
# Example request:  {"answer": "Overlapping rules are resolved by rule priority, highest wins."}
# Example response: {"id": "...", "node_id": "...", "question": "...", "status": "answered", "answer": "..."}
@router.patch("/{gap_id}", response_model=GapQuestionResponse)
def answer_gap(gap_id: UUID, body: AnswerGapRequest, db: Session = Depends(get_db)):
    """Save an answer to a gap question; the answer is embedded and folded back into the document."""
    return document_service.answer_gap(gap_id, body.answer, db)
