from uuid import UUID
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class NodeExplanationResponse(BaseModel):
    id: UUID
    node_id: UUID
    depth: str
    content: str
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
    created_at: datetime
    explanations: list[NodeExplanationResponse]

    model_config = {"from_attributes": True}


class EdgeResponse(BaseModel):
    id: UUID
    map_id: UUID
    source_node_id: UUID
    target_node_id: UUID

    model_config = {"from_attributes": True}
