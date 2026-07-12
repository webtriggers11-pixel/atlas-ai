"""
Atlas service — orchestrates LLM calls, DB persistence, and response assembly.
The router calls these functions; they never touch HTTP directly.
"""
import uuid as _uuid
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert
from fastapi import HTTPException

from app.llm import generate_concepts, generate_explanation, generate_grounded_explanation
from app.models import Map, Node, NodeExplanation, Edge, Document
from app.services.document_service import retrieve_chunks
from app.schemas import (
    FullMapResponse, MapSummary, ExpandResponse,
    NodeWithExplanations, NodeExplanationResponse, EdgeResponse,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _node_to_schema(node: Node) -> NodeWithExplanations:
    """Convert a Node ORM object (with loaded explanations) to its response schema."""
    return NodeWithExplanations(
        id=node.id,
        map_id=node.map_id,
        parent_id=node.parent_id,
        label=node.label,
        position_x=node.position_x,
        position_y=node.position_y,
        is_root=node.is_root,
        source_type=node.source_type or "topic",
        is_read=node.is_read,
        gap_status=node.gap_status or "none",
        created_at=node.created_at,
        explanations=[NodeExplanationResponse.model_validate(e) for e in node.explanations],
    )


def _build_full_map(map_row: Map) -> FullMapResponse:
    """Assemble a FullMapResponse from a Map ORM object with loaded relationships."""
    return FullMapResponse(
        id=map_row.id,
        topic=map_row.topic,
        title=map_row.title,
        created_at=map_row.created_at,
        updated_at=map_row.updated_at,
        nodes=[_node_to_schema(n) for n in map_row.nodes],
        edges=[EdgeResponse.model_validate(e) for e in map_row.edges],
    )


def _get_map_or_404(map_id: UUID, db: Session) -> Map:
    """Fetch a map by id or raise 404."""
    row = db.query(Map).filter(Map.id == map_id).first()
    if not row:
        raise HTTPException(status_code=404, detail=f"Map {map_id} not found.")
    return row


def _get_node_or_404(node_id: UUID, map_id: UUID, db: Session) -> Node:
    """Fetch a node that belongs to the given map or raise 404."""
    row = db.query(Node).filter(Node.id == node_id, Node.map_id == map_id).first()
    if not row:
        raise HTTPException(status_code=404, detail=f"Node {node_id} not found on map {map_id}.")
    return row


# ── Service functions ─────────────────────────────────────────────────────────

def create_map(topic: str, depth: str, db: Session) -> FullMapResponse:
    """Call LLM for sub-concepts, persist map/nodes/edges/explanations, return full map."""
    concept_list = generate_concepts(topic, depth)

    map_row = Map(topic=topic, title=topic)
    db.add(map_row)
    db.flush()

    root = Node(map_id=map_row.id, label=topic, is_root=True)
    db.add(root)
    db.flush()

    # Root explanation — generate separately so the root node has content on first load
    root_text = generate_explanation(topic, depth)
    db.add(NodeExplanation(node_id=root.id, depth=depth, content=root_text))

    child_nodes = []
    for concept in concept_list.concepts:
        child = Node(map_id=map_row.id, parent_id=root.id, label=concept.label)
        db.add(child)
        db.flush()

        # The LLM already gave us a summary — use it as the pre-cached explanation
        db.add(NodeExplanation(node_id=child.id, depth=depth, content=concept.summary))

        edge = Edge(map_id=map_row.id, source_node_id=root.id, target_node_id=child.id)
        db.add(edge)

        child_nodes.append(child)

    db.commit()
    db.refresh(map_row)
    return _build_full_map(map_row)


def list_maps(db: Session) -> list[MapSummary]:
    """Return a summary list of all saved maps, newest first."""
    rows = db.query(Map).order_by(Map.created_at.desc()).all()
    return [MapSummary.model_validate(r) for r in rows]


def get_map(map_id: UUID, db: Session) -> FullMapResponse:
    """Load a full saved map with all nodes, edges, and explanations."""
    map_row = _get_map_or_404(map_id, db)
    return _build_full_map(map_row)


def expand_node(map_id: UUID, node_id: UUID, depth: str, db: Session) -> ExpandResponse:
    """Generate sub-concepts for a node, persist them, and return only the new nodes/edges."""
    _get_map_or_404(map_id, db)
    node = _get_node_or_404(node_id, map_id, db)

    # Pass the node's parent label as context so the LLM stays relevant
    parent = db.query(Node).filter(Node.id == node.parent_id).first() if node.parent_id else None
    concept_list = generate_concepts(
        topic=node.label,
        depth=depth,
        parent_label=parent.label if parent else None,
        task_type="expand_small",
    )

    new_nodes = []
    new_edges = []

    for concept in concept_list.concepts:
        child = Node(map_id=map_id, parent_id=node.id, label=concept.label)
        db.add(child)
        db.flush()

        db.add(NodeExplanation(node_id=child.id, depth=depth, content=concept.summary))

        edge = Edge(map_id=map_id, source_node_id=node.id, target_node_id=child.id)
        db.add(edge)

        new_nodes.append(child)
        new_edges.append(edge)

    db.commit()
    for n in new_nodes:
        db.refresh(n)

    return ExpandResponse(
        new_nodes=[_node_to_schema(n) for n in new_nodes],
        new_edges=[EdgeResponse.model_validate(e) for e in new_edges],
    )


def change_depth(map_id: UUID, node_id: UUID, depth: str, db: Session) -> NodeExplanationResponse:
    """Return a cached explanation if it exists, otherwise call LLM, cache it, then return it."""
    _get_map_or_404(map_id, db)
    node = _get_node_or_404(node_id, map_id, db)

    # Cache hit — return immediately without calling LLM
    cached = (
        db.query(NodeExplanation)
        .filter(NodeExplanation.node_id == node_id, NodeExplanation.depth == depth)
        .first()
    )
    if cached:
        return NodeExplanationResponse.model_validate(cached)

    # Cache miss — generate content, then upsert atomically.
    # Document-grounded nodes answer ONLY from retrieved chunks (RAG);
    # topic nodes keep the original free-knowledge explanation.
    source_chunk_ids = None
    confidence = None
    section_hint = None
    document = db.query(Document).filter(Document.map_id == map_id).first()
    if document is not None and node.source_type == "document":
        results = retrieve_chunks(document.id, node.label, db, k=4)
        excerpts = "\n\n".join(
            f"[{r['chunk'].section_hint or 'Document'}]\n{r['chunk'].content}" for r in results
        )
        content = generate_grounded_explanation(node.label, depth, excerpts)
        source_chunk_ids = [str(r["chunk"].id) for r in results]
        confidence = max((r["score"] for r in results), default=None)
        section_hint = results[0]["chunk"].section_hint if results else None
    else:
        content = generate_explanation(node.label, depth)

    # INSERT ... ON CONFLICT DO NOTHING is a single atomic SQL statement:
    # if a concurrent request already inserted the same (node_id, depth) between
    # our SELECT above and this INSERT, Postgres silently skips the insert instead
    # of raising a unique-constraint error. No try/except needed.
    stmt = (
        pg_insert(NodeExplanation)
        .values(
            id=_uuid.uuid4(), node_id=node_id, depth=depth, content=content,
            source_chunk_ids=source_chunk_ids, confidence=confidence, section_hint=section_hint,
        )
        .on_conflict_do_nothing(constraint="uq_node_depth")
    )
    db.execute(stmt)
    db.commit()

    # Fetch the winner — either the row we just inserted or the one a concurrent
    # request inserted first. Either way, the client gets a valid explanation.
    result = (
        db.query(NodeExplanation)
        .filter(NodeExplanation.node_id == node_id, NodeExplanation.depth == depth)
        .first()
    )
    return NodeExplanationResponse.model_validate(result)


def mark_node_read(map_id: UUID, node_id: UUID, db: Session) -> Node:
    """Flag a node as read — idempotent, used for the 'Explored X of N' progress tracker."""
    _get_map_or_404(map_id, db)
    node = _get_node_or_404(node_id, map_id, db)
    if not node.is_read:
        node.is_read = True
        db.commit()
        db.refresh(node)
    return node


def delete_map(map_id: UUID, db: Session) -> None:
    """Delete a map and all its nodes/edges/explanations via cascade."""
    map_row = _get_map_or_404(map_id, db)
    db.delete(map_row)
    db.commit()
