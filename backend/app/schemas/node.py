from uuid import UUID
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class NodeExplanationResponse(BaseModel):
    id: UUID
    node_id: UUID
    depth: str
    content: str
    source_chunk_ids: Optional[list[str]] = None  # document chunks this answer was grounded in
    confidence: Optional[float] = None            # best chunk similarity score (0..1)
    section_hint: Optional[str] = None            # nearest heading of the top-scoring chunk
    created_at: datetime

    model_config = {"from_attributes": True}


class NodeWithExplanations(BaseModel):
    """Node plus all its cached explanations — used in full map responses."""
    id: UUID
    map_id: UUID
    parent_id: Optional[UUID]
    label: str
    position_x: Optional[float]
    position_y: Optional[float]
    is_root: bool
    source_type: str = "topic"  # 'topic' = typed topic, 'document' = grounded in an uploaded doc
    is_read: bool = False
    gap_status: str = "none"    # 'none' | 'flagged' | 'resolved'
    created_at: datetime
    explanations: list[NodeExplanationResponse]

    model_config = {"from_attributes": True}


class NodeReadResponse(BaseModel):
    id: UUID
    is_read: bool

    model_config = {"from_attributes": True}


class EdgeResponse(BaseModel):
    id: UUID
    map_id: UUID
    source_node_id: UUID
    target_node_id: UUID

    model_config = {"from_attributes": True}


# ── Gap Check ─────────────────────────────────────────────────────────────────

class GapQuestionResponse(BaseModel):
    id: UUID
    node_id: UUID
    node_label: str
    question: str
    status: str  # 'open' | 'answered'
    answer: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class GapCheckResponse(BaseModel):
    """Returned by POST /maps/{map_id}/gap-check."""
    checked_nodes: int
    flagged_nodes: int
    questions: list[GapQuestionResponse]


class AnswerGapRequest(BaseModel):
    answer: str
