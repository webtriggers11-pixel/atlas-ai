"""
Embedding service — turns text into 384-dim meaning-vectors using a small local
model (all-MiniLM-L6-v2). Runs on CPU in milliseconds; no API calls involved.
"""
import logging

logger = logging.getLogger(__name__)

_model = None  # loaded once on first use, then reused for every request


def _get_model():
    """Load all-MiniLM-L6-v2 exactly once (lazy singleton) — first call downloads ~80MB."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        logger.info("Loading all-MiniLM-L6-v2 embedding model...")
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts into normalized 384-dim vectors (one vector per text)."""
    vectors = _get_model().encode(texts, normalize_embeddings=True)
    return [v.tolist() for v in vectors]


def embed_text(text: str) -> list[float]:
    """Embed a single text into one normalized 384-dim vector."""
    return embed_texts([text])[0]
