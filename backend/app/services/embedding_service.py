"""
Embedding service — turns text into 384-dim normalized meaning-vectors.

Provider abstraction: callers use embed_text / embed_texts and never know which
backend produced the vectors.
- "local" (default): all-MiniLM-L6-v2 via sentence-transformers, CPU, no API calls.
- "fake": deterministic hashed bag-of-words vectors — used by tests so they run
  fast and offline, while texts that share words still score as similar.
"""
import hashlib
import logging
import math
import re
from typing import Protocol

from app.core.config import settings

logger = logging.getLogger(__name__)

EMBEDDING_DIM = 384


class EmbeddingProvider(Protocol):
    """Anything that can turn a batch of texts into normalized EMBEDDING_DIM-sized vectors."""

    name: str

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one normalized vector per input text."""
        ...


class LocalMiniLMProvider:
    """all-MiniLM-L6-v2 on CPU. Max input is 256 tokens (~190 words); longer text is truncated by the model."""

    name = "local-minilm"

    def __init__(self):
        """Model is loaded lazily on first use (first call downloads ~80MB)."""
        self._model = None

    def _get_model(self):
        """Load the model exactly once (lazy singleton)."""
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            logger.info("Loading %s embedding model...", settings.EMBEDDING_MODEL)
            self._model = SentenceTransformer(settings.EMBEDDING_MODEL)
        return self._model

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts into normalized vectors."""
        vectors = self._get_model().encode(texts, normalize_embeddings=True, batch_size=32)
        return [v.tolist() for v in vectors]


class FakeHashProvider:
    """Deterministic test embedder: each lower-cased word is hashed into one of 384 buckets."""

    name = "fake-hash"

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Bag-of-words hashing → L2-normalized vector; identical words give overlapping vectors."""
        vectors = []
        for text in texts:
            vec = [0.0] * EMBEDDING_DIM
            for word in re.findall(r"[a-z0-9]+", text.lower()):
                bucket = int(hashlib.md5(word.encode()).hexdigest(), 16) % EMBEDDING_DIM
                vec[bucket] += 1.0
            norm = math.sqrt(sum(v * v for v in vec)) or 1.0
            vectors.append([v / norm for v in vec])
        return vectors


_providers: dict[str, EmbeddingProvider] = {}


def get_provider() -> EmbeddingProvider:
    """Return the configured provider (cached so the model loads once per process)."""
    key = settings.EMBEDDING_PROVIDER
    if key not in _providers:
        if key == "fake":
            _providers[key] = FakeHashProvider()
        elif key == "local":
            _providers[key] = LocalMiniLMProvider()
        else:
            raise ValueError(f"Unknown EMBEDDING_PROVIDER {key!r} (use 'local' or 'fake').")
    return _providers[key]


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts into normalized 384-dim vectors (one vector per text)."""
    if not texts:
        return []
    return get_provider().embed(texts)


def embed_text(text: str) -> list[float]:
    """Embed a single text into one normalized 384-dim vector."""
    return embed_texts([text])[0]
