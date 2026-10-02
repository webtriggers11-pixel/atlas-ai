"""
Retrieval — embedding chunks at ingestion time and semantic search over them with pgvector.

Search runs inside Postgres:
    ORDER BY embedding <=> :query_vector   (cosine distance, served by the HNSW index)
so we never load every chunk into Python (what v1 did).
"""
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import DocChunk, ProjectDocument
from app.services.embedding_service import embed_text, embed_texts


@dataclass
class ScoredChunk:
    chunk: DocChunk
    document: ProjectDocument
    score: float          # cosine similarity in [-1, 1]; higher = more similar
    rank: int             # 1-based position in this result list


def embedding_input(chunk: DocChunk) -> str:
    """Text actually embedded: section title + content, so a chunk 'knows' which part of the doc it's from."""
    return f"{chunk.section}: {chunk.content}" if chunk.section else chunk.content


def embed_chunks(chunks: list[DocChunk], db: Session) -> None:
    """Compute and attach embeddings for chunks in one batch (caller commits)."""
    if not chunks:
        return
    vectors = embed_texts([embedding_input(c) for c in chunks])
    for chunk, vector in zip(chunks, vectors):
        chunk.embedding = vector
    db.flush()


def vector_search(
    project_id: UUID,
    query: str,
    db: Session,
    role: str | None = None,
    k: int = 5,
    document_ids: list[UUID] | None = None,
    query_vector: list[float] | None = None,
) -> list[ScoredChunk]:
    """Top-k chunks of a project's indexed documents by cosine similarity to the query."""
    vector = query_vector if query_vector is not None else embed_text(query)
    distance = DocChunk.embedding.cosine_distance(vector)

    # HNSW scans a candidate list of size ef_search and filters AFTER the scan; with
    # project/role filters a small list could return fewer than k rows, so raise it.
    db.execute(text(f"SET LOCAL hnsw.ef_search = {int(settings.HNSW_EF_SEARCH)}"))

    stmt = (
        select(DocChunk, ProjectDocument, distance.label("distance"))
        .join(ProjectDocument, DocChunk.document_id == ProjectDocument.id)
        .where(
            ProjectDocument.project_id == project_id,
            ProjectDocument.status == "indexed",
            DocChunk.embedding.isnot(None),
        )
        .order_by(distance)
        .limit(k)
    )
    if role:
        stmt = stmt.where(ProjectDocument.role == role)
    if document_ids:
        stmt = stmt.where(ProjectDocument.id.in_(document_ids))

    return [
        ScoredChunk(chunk=chunk, document=document, score=1.0 - float(dist), rank=i)
        for i, (chunk, document, dist) in enumerate(db.execute(stmt).all(), start=1)
    ]
