"""
Sentence-aware, section-aware chunking with page tracking.

Why these choices:
- ~180 words per chunk: the embedding model (all-MiniLM-L6-v2) reads at most
  256 tokens; anything longer is silently truncated and never embedded.
- Sentences are never cut in half, so an evidence quote stays inside one chunk.
- A new section starts a new chunk, so a chunk's `section` label is accurate.
- A small overlap (whole sentences) keeps context across chunk boundaries.
"""
import re
from dataclasses import dataclass

from app.core.config import settings
from app.services.extraction import Page

_SENTENCE_END = re.compile(r"(?<=[.!?;:])\s+(?=[\"'(\[]?[A-Z0-9])")
_NUMBERED_HEADING = re.compile(r"^(\d+(\.\d+)*\.?|[A-Z]\.)\s+[A-Z][^.]{0,80}$")


@dataclass
class Chunk:
    chunk_index: int
    content: str
    section: str | None
    page_start: int | None
    page_end: int | None
    word_count: int


@dataclass
class _Unit:
    """One sentence (or table row) with its location."""
    text: str
    section: str | None
    page: int | None
    words: int


def is_heading(line: str) -> bool:
    """Heading heuristic: '## ' markers, numbered headings ('4.2 Token Refresh'), or short Title-Case lines."""
    if line.startswith("## "):
        return True
    if " | " in line:
        return False                         # table rows are content
    if _NUMBERED_HEADING.match(line):
        return True
    words = line.split()
    if not 1 <= len(words) <= 8 or len(line) > 70 or line.endswith((".", ",", ";", ":")):
        return False
    capitalized = sum(1 for w in words if w[0].isupper() or not w[0].isalpha())
    return capitalized / len(words) >= 0.75 and any(w[0].isalpha() for w in words)


def _split_sentences(line: str) -> list[str]:
    """Split a line into sentences; table rows and short lines stay whole."""
    if " | " in line or len(line.split()) <= 25:
        return [line]
    return [s.strip() for s in _SENTENCE_END.split(line) if s.strip()]


def _units(pages: list[Page]) -> list[_Unit]:
    """Flatten pages into sentences tagged with the current section heading and page number."""
    units: list[_Unit] = []
    section: str | None = None
    for page in pages:
        for line in page.text.splitlines():
            line = line.strip()
            if not line:
                continue
            if is_heading(line):
                section = line.removeprefix("## ").strip()
                continue
            for sentence in _split_sentences(line):
                units.append(_Unit(sentence, section, page.number, len(sentence.split())))
    return units


def _split_oversized(units: list[_Unit], max_words: int) -> list[_Unit]:
    """Break any single sentence longer than max_words into word windows so no chunk exceeds the limit."""
    result = []
    for unit in units:
        if unit.words <= max_words:
            result.append(unit)
            continue
        words = unit.text.split()
        for start in range(0, len(words), max_words):
            piece = words[start:start + max_words]
            result.append(_Unit(" ".join(piece), unit.section, unit.page, len(piece)))
    return result


def chunk_pages(pages: list[Page], max_words: int | None = None, overlap_words: int | None = None) -> list[Chunk]:
    """Pack sentences into chunks of at most ~max_words, breaking at section changes, with sentence overlap."""
    max_words = max_words or settings.CHUNK_WORDS
    overlap_words = settings.CHUNK_OVERLAP_WORDS if overlap_words is None else overlap_words

    chunks: list[Chunk] = []
    current: list[_Unit] = []

    def flush():
        """Emit the current sentences as one chunk."""
        if not current:
            return
        pages_seen = [u.page for u in current if u.page is not None]
        chunks.append(Chunk(
            chunk_index=len(chunks),
            content=" ".join(u.text for u in current),
            section=current[0].section,
            page_start=min(pages_seen) if pages_seen else None,
            page_end=max(pages_seen) if pages_seen else None,
            word_count=sum(u.words for u in current),
        ))

    def overlap_tail() -> list[_Unit]:
        """Last whole sentences of the current chunk totalling <= overlap_words (same section only)."""
        tail, words = [], 0
        for unit in reversed(current):
            if words + unit.words > overlap_words:
                break
            tail.insert(0, unit)
            words += unit.words
        return tail

    for unit in _split_oversized(_units(pages), max_words):
        size = sum(u.words for u in current)
        section_changed = bool(current) and unit.section != current[-1].section
        if section_changed:
            flush()
            current = []
        elif current and size + unit.words > max_words:
            tail = overlap_tail()
            flush()
            current = tail if sum(u.words for u in tail) + unit.words <= max_words else []
        current.append(unit)

    flush()
    return chunks
