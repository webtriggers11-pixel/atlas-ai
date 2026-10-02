"""
Retrieval — embedding chunks at ingestion time and searching them.

Three search strategies, all running inside Postgres:
- vector:  ORDER BY embedding <=> :query_vector       (meaning; HNSW index)
- keyword: ts_rank_cd(tsv, query) over a tsvector     (exact words / identifiers; GIN index)
- hybrid:  both rankings fused with Reciprocal Rank Fusion (RRF):
           score(chunk) = Σ 1 / (RRF_K + rank_in_list)
RRF only uses ranks, so the two very different score scales never need calibrating.
"""
from dataclasses import dataclass
from uuid import UUID

import numpy as np
from sqlalchemy import Text, cast, func, select, text
from sqlalchemy.dialects.postgresql import TSQUERY
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import DocChunk, ProjectDocument
from app.services.embedding_service import embed_text, embed_texts


@dataclass
class ScoredChunk:
    chunk: DocChunk
    document: ProjectDocument
    score: float          # cosine similarity in [-1, 1]; higher = more similar (used by guardrails)
    rank: int             # 1-based position in this result list
    fused: float = 0.0    # RRF score (hybrid only)


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


def _scope(stmt, project_id: UUID, role: str | None, document_ids: list[UUID] | None):
    """Restrict a chunk query to one project's indexed documents (optionally one role / some documents)."""
    stmt = stmt.join(ProjectDocument, DocChunk.document_id == ProjectDocument.id).where(
        ProjectDocument.project_id == project_id, ProjectDocument.status == "indexed")
    if role:
        stmt = stmt.where(ProjectDocument.role == role)
    if document_ids:
        stmt = stmt.where(ProjectDocument.id.in_(document_ids))
    return stmt


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

    stmt = _scope(select(DocChunk, ProjectDocument, distance.label("distance")), project_id, role, document_ids)
    stmt = stmt.where(DocChunk.embedding.isnot(None)).order_by(distance).limit(k)
    return [
        ScoredChunk(chunk=chunk, document=document, score=1.0 - float(dist), rank=i)
        for i, (chunk, document, dist) in enumerate(db.execute(stmt).all(), start=1)
    ]


def keyword_search(
    project_id: UUID,
    query: str,
    db: Session,
    role: str | None = None,
    k: int = 5,
    document_ids: list[UUID] | None = None,
) -> list[tuple[DocChunk, ProjectDocument]]:
    """Top-k chunks by full-text rank. Terms are OR-ed: a long requirement sentence rarely matches every word."""
    # plainto_tsquery stems words and drops stop-words; swapping '&' for '|' turns AND into OR
    ts_query = cast(func.replace(cast(func.plainto_tsquery("english", query), Text), "&", "|"), TSQUERY)
    rank = func.ts_rank_cd(DocChunk.tsv, ts_query)
    stmt = _scope(select(DocChunk, ProjectDocument), project_id, role, document_ids)
    stmt = stmt.where(DocChunk.tsv.op("@@")(ts_query)).order_by(rank.desc()).limit(k)
    return list(db.execute(stmt).all())


def hybrid_search(
    project_id: UUID,
    queries: list[str],
    db: Session,
    role: str | None = None,
    k: int = 5,
    document_ids: list[UUID] | None = None,
) -> list[ScoredChunk]:
    """RRF fusion of vector + keyword rankings for one or more phrasings of the same need.

    Each (query, method) pair contributes one ranked list; a chunk's fused score is
    Σ 1/(RRF_K + rank). `score` stays the best cosine similarity to any phrasing so
    downstream thresholds (e.g. the missing-guard) keep a meaningful scale.
    """
    n = settings.HYBRID_CANDIDATES
    vectors = embed_texts(queries)
    fused: dict[UUID, float] = {}
    rows: dict[UUID, tuple[DocChunk, ProjectDocument]] = {}

    for query, vector in zip(queries, vectors):
        for hit in vector_search(project_id, query, db, role, n, document_ids, query_vector=vector):
            rows[hit.chunk.id] = (hit.chunk, hit.document)
            fused[hit.chunk.id] = fused.get(hit.chunk.id, 0.0) + 1.0 / (settings.RRF_K + hit.rank)
        for rank, (chunk, document) in enumerate(keyword_search(project_id, query, db, role, n, document_ids), start=1):
            rows[chunk.id] = (chunk, document)
            fused[chunk.id] = fused.get(chunk.id, 0.0) + 1.0 / (settings.RRF_K + rank)

    top = sorted(fused, key=fused.get, reverse=True)[:k]
    query_matrix = np.array(vectors)
    results = []
    for i, chunk_id in enumerate(top, start=1):
        chunk, document = rows[chunk_id]
        similarity = float((query_matrix @ np.asarray(chunk.embedding)).max()) if chunk.embedding is not None else 0.0
        results.append(ScoredChunk(chunk=chunk, document=document, score=similarity, rank=i, fused=round(fused[chunk_id], 5)))
    return results


def search(
    project_id: UUID,
    query: str,
    db: Session,
    role: str | None = None,
    k: int = 5,
    mode: str | None = None,
    extra_queries: list[str] | None = None,
) -> list[ScoredChunk]:
    """Search with the configured (or given) mode; extra_queries are alternative phrasings (hybrid only)."""
    mode = mode or settings.RETRIEVAL_MODE
    if mode == "vector":
        return vector_search(project_id, query, db, role=role, k=k)
    return hybrid_search(project_id, [query, *(extra_queries or [])], db, role=role, k=k)


def search_evidence(
    project_id: UUID, requirement_text: str, db: Session, k: int | None = None, extra_queries: list[str] | None = None,
) -> list[ScoredChunk]:
    """Evidence candidates for one requirement: the top-k chunks of the project's EXISTING documents."""
    return search(project_id, requirement_text, db, role="existing", k=k or settings.EVIDENCE_K, extra_queries=extra_queries)
