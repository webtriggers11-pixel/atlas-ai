from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import (
    CreateMapRequest, ExpandNodeRequest, ChangeDepthRequest,
    FullMapResponse, MapSummary, ExpandResponse, NodeExplanationResponse, NodeReadResponse,
    GapCheckResponse,
)
from app.services import atlas_service
from app.services import document_service

router = APIRouter(prefix="/maps", tags=["maps"])


# POST /maps
# Example request:  {"topic": "quantum computing", "depth": "standard"}
# Example response: FullMapResponse with nodes, edges, explanations
@router.post("", response_model=FullMapResponse, status_code=status.HTTP_201_CREATED)
def create_map(body: CreateMapRequest, db: Session = Depends(get_db)):
    """Generate a new concept map from a topic and persist it."""
    return atlas_service.create_map(body.topic, body.depth, db)


# GET /maps
# Example response: [{"id": "...", "topic": "quantum computing", "created_at": "..."}]
@router.get("", response_model=list[MapSummary])
def list_maps(db: Session = Depends(get_db)):
    """Return all saved maps newest-first for the recent maps panel."""
    return atlas_service.list_maps(db)


# GET /maps/{map_id}
# Example response: FullMapResponse with all nodes and edges
@router.get("/{map_id}", response_model=FullMapResponse)
def get_map(map_id: UUID, db: Session = Depends(get_db)):
    """Load a previously saved map with all its nodes, edges, and explanations."""
    return atlas_service.get_map(map_id, db)


# POST /maps/{map_id}/nodes/{node_id}/expand
# Example request:  {"depth": "standard"}
# Example response: {"new_nodes": [...], "new_edges": [...]}
@router.post("/{map_id}/nodes/{node_id}/expand", response_model=ExpandResponse)
def expand_node(map_id: UUID, node_id: UUID, body: ExpandNodeRequest, db: Session = Depends(get_db)):
    """Expand a node into its own sub-concepts and return only the new nodes and edges."""
    return atlas_service.expand_node(map_id, node_id, body.depth, db)


# PATCH /maps/{map_id}/nodes/{node_id}/depth
# Example request:  {"depth": "expert"}
# Example response: {"id": "...", "node_id": "...", "depth": "expert", "content": "..."}
@router.patch("/{map_id}/nodes/{node_id}/depth", response_model=NodeExplanationResponse)
def change_depth(map_id: UUID, node_id: UUID, body: ChangeDepthRequest, db: Session = Depends(get_db)):
    """Return a cached explanation or generate a new one at the requested depth."""
    return atlas_service.change_depth(map_id, node_id, body.depth, db)


# PATCH /maps/{map_id}/nodes/{node_id}/read
# Example response: {"id": "...", "is_read": true}
@router.patch("/{map_id}/nodes/{node_id}/read", response_model=NodeReadResponse)
def mark_node_read(map_id: UUID, node_id: UUID, db: Session = Depends(get_db)):
    """Flag a node as read for the map's progress tracker."""
    return atlas_service.mark_node_read(map_id, node_id, db)


# POST /maps/{map_id}/gap-check
# Example response: {"checked_nodes": 11, "flagged_nodes": 3, "questions": [...]}
@router.post("/{map_id}/gap-check", response_model=GapCheckResponse)
def gap_check(map_id: UUID, db: Session = Depends(get_db)):
    """Flag under-documented nodes and generate developer questions for each (document maps only)."""
    return document_service.gap_check_map(map_id, db)


# GET /maps/{map_id}/gaps
# Example response: {"checked_nodes": 11, "flagged_nodes": 3, "questions": [...]}
@router.get("/{map_id}/gaps", response_model=GapCheckResponse)
def list_gaps(map_id: UUID, db: Session = Depends(get_db)):
    """Return all gap questions for a map's nodes."""
    return document_service.list_gaps(map_id, db)


# DELETE /maps/{map_id}
# Example response: 204 No Content
@router.delete("/{map_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_map(map_id: UUID, db: Session = Depends(get_db)):
    """Delete a map and all its nodes, edges, and explanations."""
    atlas_service.delete_map(map_id, db)
