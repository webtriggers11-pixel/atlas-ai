from uuid import UUID
from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel
from app.schemas.node import NodeWithExplanations, EdgeResponse


# ── Requests ──────────────────────────────────────────────────────────────────

class CreateMapRequest(BaseModel):
    topic: str
    depth: Literal["gist", "standard", "expert"] = "standard"


class ExpandNodeRequest(BaseModel):
    depth: Literal["gist", "standard", "expert"] = "standard"


class ChangeDepthRequest(BaseModel):
    depth: Literal["gist", "standard", "expert"]


# ── Responses ─────────────────────────────────────────────────────────────────

class MapSummary(BaseModel):
    """Lightweight row for the recent maps list — no nodes or edges."""
    id: UUID
    topic: str
    title: str
    created_at: datetime

    model_config = {"from_attributes": True}


class FullMapResponse(BaseModel):
    """Complete map returned by POST /maps and GET /maps/{id}."""
    id: UUID
    topic: str
    title: str
    created_at: datetime
    updated_at: datetime
    nodes: list[NodeWithExplanations]
    edges: list[EdgeResponse]

    model_config = {"from_attributes": True}


class ExpandResponse(BaseModel):
    """New nodes and edges created by POST .../expand."""
    new_nodes: list[NodeWithExplanations]
    new_edges: list[EdgeResponse]
