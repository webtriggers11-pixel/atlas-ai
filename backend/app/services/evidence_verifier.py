"""
Evidence verification — deterministic code that checks the LLM's quotes really exist.

LLMs sometimes "quote" text that is not in the source (paraphrases or inventions).
Before a quote is stored as evidence we look for it in the chunk it claims to come
from: first as an exact match after light normalization, then as a fuzzy match over
word windows (ratio ≥ 0.9). The stored quote is the matching span from the SOURCE,
never the model's version, so what the user sees is always real document text.
"""
import re
from dataclasses import dataclass
from difflib import SequenceMatcher

FUZZY_THRESHOLD = 0.90

_QUOTE_CHARS = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-"})


@dataclass
class VerifiedQuote:
    verified: bool
    text: str          # span copied from the source when verified, else the model's quote
    ratio: float


def _norm(text: str) -> str:
    """Lowercase, unify quote/dash characters, collapse whitespace, trim surrounding punctuation."""
    text = text.translate(_QUOTE_CHARS).lower()
    text = re.sub(r"\s+", " ", text).strip()
    return text.strip(" .,;:\"'()[]")


def verify_quote(quote: str, source: str) -> VerifiedQuote:
    """Return whether `quote` appears in `source` (exactly or ≥90% fuzzy) and the matching source span."""
    q = _norm(quote)
    if len(q) < 3:
        return VerifiedQuote(False, quote, 0.0)

    words = source.split()
    norm_words = [_norm(w) for w in words]
    q_words = q.split()
    n = len(q_words)

    best_ratio, best_span = 0.0, None
    # Slide a window of roughly the quote's length over the source words
    for size in {max(1, n - 2), max(1, n - 1), n, n + 1, n + 2}:
        for start in range(0, max(1, len(words) - size + 1)):
            window = " ".join(w for w in norm_words[start:start + size] if w)
            if window == q:
                return VerifiedQuote(True, " ".join(words[start:start + size]), 1.0)
            ratio = SequenceMatcher(None, q, window).ratio()
            if ratio > best_ratio:
                best_ratio, best_span = ratio, " ".join(words[start:start + size])

    if best_ratio >= FUZZY_THRESHOLD and best_span:
        return VerifiedQuote(True, best_span, best_ratio)
    return VerifiedQuote(False, quote, best_ratio)
