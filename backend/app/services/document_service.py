"""
Document service — extracts plain text from uploaded files, slices it into
overlapping chunks, embeds them, and orchestrates building a grounded map.
"""
import io
import time
from pathlib import PurePath
from fastapi import HTTPException
from sqlalchemy.orm import Session

MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MB upload cap

CHUNK_WORDS = 500    # target chunk size
OVERLAP_WORDS = 50   # words shared between consecutive chunks so ideas aren't cut mid-thought


# ── Extraction ────────────────────────────────────────────────────────────────

def _extract_docx(data: bytes) -> str:
    """Pull text from a .docx, writing real Heading-styled paragraphs as '## <text>' marker lines."""
    import docx
    document = docx.Document(io.BytesIO(data))
    lines = []
    for para in document.paragraphs:
        text = para.text.strip()
        if not text:
            continue
        if para.style.name.startswith("Heading"):
            lines.append(f"## {text}")
        else:
            lines.append(text)
    return "\n".join(lines)


def _extract_pdf(data: bytes) -> str:
    """Pull text from a PDF page by page."""
    import pypdf
    reader = pypdf.PdfReader(io.BytesIO(data))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages)


def extract_text(data: bytes | str, source_type: str) -> str:
    """Extract plain text from an upload: docx and pdf bytes are parsed, pasted text passes through."""
    if source_type == "pasted":
        text = data if isinstance(data, str) else data.decode("utf-8", errors="replace")
        if len(text.encode("utf-8")) > MAX_FILE_BYTES:
            raise HTTPException(status_code=413, detail="Pasted text exceeds the 10 MB limit.")
        return text

    if not isinstance(data, bytes):
        raise HTTPException(status_code=400, detail=f"Expected file bytes for source_type '{source_type}'.")
    if len(data) > MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds the 10 MB limit.")

    if source_type == "docx":
        return _extract_docx(data)
    if source_type == "pdf":
        return _extract_pdf(data)
    raise HTTPException(status_code=400, detail=f"Unsupported source_type '{source_type}'. Use docx, pdf, or pasted.")


# ── Chunking ──────────────────────────────────────────────────────────────────

def _looks_like_heading(line: str) -> bool:
    """Heuristic: '## ' markers are always headings; otherwise short, mostly-capitalized lines count."""
    if line.startswith("#"):
        return True
    words = line.split()
    if not 1 <= len(words) <= 8 or len(line) > 60:
        return False
    if line.endswith((".", ",", ";")):
        return False
    capitalized = sum(1 for w in words if w[0].isupper())
    return capitalized / len(words) >= 0.6


def chunk_text(full_text: str) -> list[dict]:
    """Split text into ~500-word chunks with 50-word overlap, tagging each with the nearest heading above it."""
    # Walk the text line by line, remembering which heading each word sits under
    words: list[tuple[str, str | None]] = []
    current_heading: str | None = None
    for line in full_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if _looks_like_heading(stripped):
            current_heading = stripped.lstrip("#").strip()
            continue
        for word in stripped.split():
            words.append((word, current_heading))

    chunks = []
    step = CHUNK_WORDS - OVERLAP_WORDS
    start = 0
    while start < len(words):
        window = words[start : start + CHUNK_WORDS]
        chunks.append({
            "chunk_index": len(chunks),
            "content": " ".join(w for w, _ in window),
            "section_hint": window[0][1],
        })
        if start + CHUNK_WORDS >= len(words):
            break
        start += step
    return chunks


# ── Grounded retrieval ────────────────────────────────────────────────────────

def retrieve_chunks(document_id, query: str, db: Session, k: int = 4) -> list[dict]:
    """Return the k document chunks most similar to the query, with scores and section hints."""
    import numpy as np
    from app.models import DocumentChunk
    from app.services.embedding_service import embed_text

    chunks = (
        db.query(DocumentChunk)
        .filter(DocumentChunk.document_id == document_id, DocumentChunk.embedding.isnot(None))
        .all()
    )
    if not chunks:
        return []

    query_vector = np.array(embed_text(query))
    chunk_matrix = np.array([c.embedding for c in chunks])
    # vectors are normalized, so dot product == cosine similarity
    scores = chunk_matrix @ query_vector

    top_indices = np.argsort(scores)[::-1][:k]
    return [{"chunk": chunks[i], "score": float(scores[i])} for i in top_indices]


# ── Map building from a document ──────────────────────────────────────────────

def _build_outline(chunks: list[dict]) -> str:
    """Compose the document's headings plus the first chunk of each section into a compact LLM input."""
    first_chunk_per_section: dict[str, str] = {}
    for chunk in chunks:
        hint = chunk["section_hint"] or "Document start"
        if hint not in first_chunk_per_section:
            first_chunk_per_section[hint] = chunk["content"]

    parts = ["SECTIONS: " + " | ".join(first_chunk_per_section)]
    for hint, content in first_chunk_per_section.items():
        excerpt = " ".join(content.split()[:200])  # cap each section sample at 200 words
        parts.append(f"## {hint}\n{excerpt}")
    return "\n\n".join(parts)


def create_document_map(data: bytes | str, filename: str, source_type: str, db: Session):
    """Full upload pipeline: extract → chunk → embed → store → LLM hierarchy → build grounded map."""
    from app.llm import generate_document_hierarchy
    from app.models import Document, DocumentChunk, Map, Node, NodeExplanation, Edge
    from app.services.atlas_service import _build_full_map
    from app.services.embedding_service import embed_texts
    from app.schemas import DocumentMapResponse

    t0 = time.perf_counter()
    full_text = extract_text(data, source_type)
    if not full_text.strip():
        raise HTTPException(status_code=422, detail="No readable text found in the document.")
    print(f"[upload] extracted {len(full_text.split())} words ({int((time.perf_counter() - t0) * 1000)} ms)")

    t1 = time.perf_counter()
    chunks = chunk_text(full_text)
    print(f"[upload] chunked into {len(chunks)} chunks ({int((time.perf_counter() - t1) * 1000)} ms)")

    t2 = time.perf_counter()
    vectors = embed_texts([c["content"] for c in chunks])
    print(f"[upload] embedded {len(vectors)} chunks ({int((time.perf_counter() - t2) * 1000)} ms)")

    doc = Document(filename=filename, source_type=source_type, full_text=full_text)
    db.add(doc)
    db.flush()
    for chunk, vector in zip(chunks, vectors):
        db.add(DocumentChunk(
            document_id=doc.id,
            chunk_index=chunk["chunk_index"],
            content=chunk["content"],
            embedding=vector,
            section_hint=chunk["section_hint"],
        ))

    t3 = time.perf_counter()
    hierarchy = generate_document_hierarchy(_build_outline(chunks))
    print(f"[upload] map built: {len(hierarchy.concepts)} concepts ({int((time.perf_counter() - t3) * 1000)} ms)")

    title = PurePath(filename).stem or filename
    map_row = Map(topic=title, title=title)
    db.add(map_row)
    db.flush()

    root = Node(map_id=map_row.id, label=title, is_root=True, source_type="document")
    db.add(root)
    db.flush()
    db.add(NodeExplanation(
        node_id=root.id, depth="standard",
        content=f"Concept map built from your document '{filename}'. Every node is grounded in the document text.",
    ))

    # Pass 1 — create one node per unique concept label
    label_to_node: dict[str, Node] = {}
    for concept in hierarchy.concepts:
        if concept.label in label_to_node or concept.label == title:
            continue  # skip duplicate labels the LLM occasionally produces
        node = Node(map_id=map_row.id, label=concept.label, source_type="document")
        db.add(node)
        db.flush()
        db.add(NodeExplanation(node_id=node.id, depth="standard", content=concept.summary))
        label_to_node[concept.label] = node

    # Pass 2 — wire parents and edges now that every node exists
    for concept in hierarchy.concepts:
        node = label_to_node.get(concept.label)
        if node is None:
            continue
        parent = label_to_node.get(concept.parent_label) if concept.parent_label else None
        if parent is None or parent.id == node.id:
            parent = root  # unknown or self-referencing parent → attach to root
        node.parent_id = parent.id
        db.add(Edge(map_id=map_row.id, source_node_id=parent.id, target_node_id=node.id))

    doc.map_id = map_row.id
    db.commit()
    db.refresh(map_row)

    full_map = _build_full_map(map_row)
    return DocumentMapResponse(
        **full_map.model_dump(),
        document_id=doc.id,
        document_filename=doc.filename,
        chunk_count=len(chunks),
    )


# ── Gap Check ─────────────────────────────────────────────────────────────────

def _get_document_for_map(map_id, db: Session):
    """Return the Document backing a map, or raise 400 if the map wasn't built from a document."""
    from app.models import Document
    from fastapi import HTTPException as _HTTPException

    document = db.query(Document).filter(Document.map_id == map_id).first()
    if document is None:
        raise _HTTPException(status_code=400, detail="Gap Check only applies to document-grounded maps.")
    return document


def gap_check_map(map_id, db: Session):
    """
    For every non-root node, retrieve its best-matching chunks. If the best similarity is
    below GAP_THRESHOLD, flag the node as under-documented and ask the LLM what a developer
    would still need answered. Re-running this is safe: previously-answered gaps are kept,
    only 'open' gaps get regenerated (an answer that raised the node's similarity above the
    threshold will simply stop the node from being re-flagged next time).
    """
    from app.core.config import settings
    from app.models import Node, NodeGap
    from app.llm import generate_gap_questions
    from app.schemas import GapCheckResponse, GapQuestionResponse

    document = _get_document_for_map(map_id, db)
    nodes = db.query(Node).filter(Node.map_id == map_id, Node.is_root.is_(False)).all()

    flagged = 0
    all_new_questions = []
    for node in nodes:
        results = retrieve_chunks(document.id, node.label, db, k=4)
        best_score = results[0]["score"] if results else 0.0

        if best_score < settings.GAP_THRESHOLD:
            flagged += 1
            node.gap_status = "flagged"
            # Clear stale open questions before regenerating — keep answered ones as history
            db.query(NodeGap).filter(NodeGap.node_id == node.id, NodeGap.status == "open").delete()

            excerpts = "\n\n".join(
                f"[{r['chunk'].section_hint or 'Document'}]\n{r['chunk'].content}" for r in results
            ) or "(nothing relevant found in the document)"
            questions = generate_gap_questions(node.label, excerpts)
            for q in questions:
                gap = NodeGap(node_id=node.id, question=q)
                db.add(gap)
                all_new_questions.append(gap)
        else:
            # No longer under-documented (e.g. a prior answer raised its similarity) —
            # only clear the flag if every question on it has already been answered.
            still_open = db.query(NodeGap).filter(NodeGap.node_id == node.id, NodeGap.status == "open").count()
            if still_open == 0:
                node.gap_status = "none"

    db.commit()
    for gap in all_new_questions:
        db.refresh(gap)

    return GapCheckResponse(
        checked_nodes=len(nodes),
        flagged_nodes=flagged,
        questions=[
            GapQuestionResponse(
                id=g.id, node_id=g.node_id, node_label=g.node.label,
                question=g.question, status=g.status, answer=g.answer, created_at=g.created_at,
            )
            for g in all_new_questions
        ],
    )


def list_gaps(map_id, db: Session):
    """Return every gap question for a map's nodes, newest first."""
    from app.models import Node, NodeGap
    from app.schemas import GapCheckResponse, GapQuestionResponse

    gaps = (
        db.query(NodeGap)
        .join(Node, Node.id == NodeGap.node_id)
        .filter(Node.map_id == map_id)
        .order_by(NodeGap.created_at.desc())
        .all()
    )
    flagged = db.query(Node).filter(Node.map_id == map_id, Node.gap_status == "flagged").count()

    return GapCheckResponse(
        checked_nodes=db.query(Node).filter(Node.map_id == map_id, Node.is_root.is_(False)).count(),
        flagged_nodes=flagged,
        questions=[
            GapQuestionResponse(
                id=g.id, node_id=g.node_id, node_label=g.node.label,
                question=g.question, status=g.status, answer=g.answer, created_at=g.created_at,
            )
            for g in gaps
        ],
    )


def answer_gap(gap_id, answer: str, db: Session):
    """
    Save an answer to a gap question and fold it back into the document as a new,
    embedded chunk — so future explanations and future gap-checks can see it too.
    This is what makes the tool improve the document over time instead of just critiquing it.
    """
    from app.models import NodeGap, DocumentChunk, Document
    from app.services.embedding_service import embed_text
    from app.schemas import GapQuestionResponse
    from fastapi import HTTPException as _HTTPException

    gap = db.query(NodeGap).filter(NodeGap.id == gap_id).first()
    if gap is None:
        raise _HTTPException(status_code=404, detail=f"Gap question {gap_id} not found.")

    gap.answer = answer
    gap.status = "answered"

    node = gap.node
    document = db.query(Document).filter(Document.map_id == node.map_id).first()
    if document is not None:
        next_index = (
            db.query(DocumentChunk).filter(DocumentChunk.document_id == document.id).count()
        )
        db.add(DocumentChunk(
            document_id=document.id,
            chunk_index=next_index,
            content=f"Q: {gap.question}\nA: {answer}",
            embedding=embed_text(answer),
            section_hint=f"Answered: {node.label}",
        ))

    # If every gap on this node is now answered, flip its marker from amber to resolved (green)
    still_open = db.query(NodeGap).filter(NodeGap.node_id == node.id, NodeGap.status == "open").count()
    if still_open == 0:
        node.gap_status = "resolved"

    db.commit()
    db.refresh(gap)

    return GapQuestionResponse(
        id=gap.id, node_id=gap.node_id, node_label=node.label,
        question=gap.question, status=gap.status, answer=gap.answer, created_at=gap.created_at,
    )
