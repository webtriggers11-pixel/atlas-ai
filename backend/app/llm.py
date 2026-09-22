"""
All LLM calls live here and ONLY here.
Switching providers (ollama ↔ groq) means editing only this file — nothing else changes.
"""
import json
import logging
import time
import httpx
from pydantic import BaseModel, ValidationError
from fastapi import HTTPException
from app.core.config import settings

logger = logging.getLogger(__name__)


class RateLimited(Exception):
    """Raised when a provider returns HTTP 429 or 503 so _call_llm can retry with another provider."""


# ── Response shape ────────────────────────────────────────────────────────────

class Concept(BaseModel):
    label: str
    summary: str


class ConceptList(BaseModel):
    concepts: list[Concept]


class HierarchyConcept(BaseModel):
    label: str
    summary: str
    parent_label: str | None = None


class HierarchyList(BaseModel):
    concepts: list[HierarchyConcept]


class GapQuestions(BaseModel):
    questions: list[str]


# ── Prompt templates ──────────────────────────────────────────────────────────

_DEPTH_RULE = {
    "gist":     "Each summary: ONE sentence, under 15 words, plain everyday language.",
    "standard": "Each summary: ONE clear sentence, accessible to a curious non-expert.",
    "expert":   "Each summary: ONE precise technical sentence using domain terminology.",
}

# Few-shot system prompt — kept short to stay within Groq free-tier TPM limits
_SYSTEM_CONCEPTS = """\
Return ONLY a JSON object — no text before or after it.
Format: {{"concepts":[{{"label":"2-5 word name","summary":"one sentence"}}]}}
Give 6 sub-concepts. Rule: {depth_rule}
Example input: "machine learning"
Example output: {{"concepts":[{{"label":"Supervised learning","summary":"Training on labeled data to predict outputs."}},{{"label":"Neural networks","summary":"Layered functions that learn patterns from data."}},{{"label":"Overfitting","summary":"Model memorises training data and fails on new inputs."}}]}}\
"""

# Sent as a follow-up user message when attempt 1 returns bad JSON
# (single braces — this string is sent raw, it never goes through .format())
_RETRY_MSG = """\
Your previous response was not valid JSON. This is your only retry.

Return ONLY this structure — nothing before it, nothing after it:
{"concepts": [{"label": "...", "summary": "..."}, ...]}\
"""

# Few-shot prompt for building a concept hierarchy grounded in an uploaded document.
# Sent raw (no .format()) so braces are single.
_SYSTEM_DOC_HIERARCHY = """\
You build a concept hierarchy of a document. Base it ONLY on the document content provided — never invent concepts the document does not mention.
Return ONLY a JSON object — no text before or after it.
Format: {"concepts":[{"label":"2-5 word name","summary":"one sentence grounded in the document","parent_label":null}]}
Rules: 8-15 concepts total. Top-level concepts use parent_label null. Sub-concepts set parent_label to their parent concept's EXACT label.
Example output: {"concepts":[{"label":"Ingestion rules","summary":"Rules controlling which sensor observations enter the system.","parent_label":null},{"label":"Visibility windows","summary":"Time ranges during which observations are accepted.","parent_label":"Ingestion rules"}]}\
"""

_SYSTEM_EXPLANATION = "Return ONLY plain prose. No JSON, no markdown, no bullets. Just the explanation."

# Few-shot prompt for gap-check: given everything a document says about a concept,
# list the specific questions a developer would still need answered.
# Sent raw (no .format()) so braces are single.
_SYSTEM_GAP_QUESTIONS = """\
A developer must implement the concept described below. Given everything the document says about it, list 2-4 SPECIFIC questions a developer would need answered that this text does NOT answer.
Focus on concrete implementation gaps: exact values, edge cases, error handling, limits, defaults — not vague requests for "more detail".
Return ONLY a JSON object — no text before or after it.
Format: {"questions":["question 1","question 2"]}
Example output: {"questions":["What happens when two ingestion rules overlap for the same sensor?","Is the debounce window configurable per-site or fixed globally?"]}\
"""

_RETRY_GAP_MSG = """\
Your previous response was not valid JSON. This is your only retry.

Return ONLY this structure — nothing before it, nothing after it:
{"questions": ["...", "..."]}\
"""

# Grounded mode — the model may ONLY use the supplied document excerpts
_SYSTEM_GROUNDED = """\
You are explaining a concept from a specific document.
RULES:
- Answer ONLY from the excerpts the user provides.
- If the excerpts do not contain the answer, reply exactly: The document does not cover this.
- Never use outside knowledge. Never guess.
Return ONLY plain prose. No JSON, no markdown, no bullets.\
"""

_DEPTH_EXPLANATION = {
    "gist":     "one sentence under 15 words, plain language",
    "standard": "2-3 clear sentences, accessible to a non-expert",
    "expert":   "3-4 sentences using precise technical terminology",
}


# ── Provider calls ─────────────────────────────────────────────────────────────

def _call_ollama(messages: list[dict]) -> str:
    """POST to local Ollama /api/chat and return the assistant message text."""
    try:
        resp = httpx.post(
            f"{settings.OLLAMA_BASE_URL}/api/chat",
            json={
                "model": settings.OLLAMA_MODEL,
                "messages": messages,
                "stream": False,
                "keep_alive": -1,   # keep model in RAM indefinitely — eliminates cold-start delays
            },
            timeout=300.0,
        )
    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail="Local AI model isn't running. Start Ollama and try again.",
        )
    except httpx.ReadTimeout:
        raise HTTPException(
            status_code=503,
            detail="Ollama took too long to respond. The model may still be loading — wait a moment and try again.",
        )
    except httpx.RemoteProtocolError:
        raise HTTPException(
            status_code=503,
            detail="Ollama disconnected before responding. The model likely ran out of memory — try 'ollama run phi3:mini' instead of llama3.1:8b.",
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Ollama error {resp.status_code}: {resp.text}")
    return resp.json()["message"]["content"]


def _call_groq(messages: list[dict]) -> str:
    """POST to Groq /chat/completions (OpenAI-compatible) and return the assistant message text."""
    try:
        resp = httpx.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
            json={"model": settings.GROQ_MODEL, "messages": messages, "temperature": 0.3, "max_tokens": 600},
            timeout=30.0,
        )
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Cannot reach Groq API. Check your network.")
    if resp.status_code in (429, 503):
        raise RateLimited(f"Groq unavailable ({resp.status_code}): {resp.text[:200]}")
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Groq error {resp.status_code}: {resp.text}")
    return resp.json()["choices"][0]["message"]["content"]


def _messages_to_gemini_prompt(messages: list[dict]) -> str:
    """Flatten an OpenAI-style message list into one text prompt for Gemini's contents format."""
    parts = []
    for msg in messages:
        if msg["role"] == "system":
            parts.append(f"INSTRUCTIONS:\n{msg['content']}")
        elif msg["role"] == "assistant":
            parts.append(f"YOUR PREVIOUS RESPONSE:\n{msg['content']}")
        else:
            parts.append(msg["content"])
    return "\n\n".join(parts)


def _call_gemini(messages: list[dict]) -> str:
    """POST to Google Gemini generateContent and return the reply text."""
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.GEMINI_MODEL}:generateContent"
    )
    try:
        resp = httpx.post(
            url,
            # Key goes in a header, not the URL — URLs end up in server logs, headers don't
            headers={"X-goog-api-key": settings.GEMINI_API_KEY},
            json={"contents": [{"parts": [{"text": _messages_to_gemini_prompt(messages)}]}]},
            timeout=60.0,
        )
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Cannot reach Gemini API. Check your network.")
    if resp.status_code in (429, 503):
        raise RateLimited(f"Gemini unavailable ({resp.status_code}): {resp.text[:200]}")
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Gemini error {resp.status_code}: {resp.text}")
    try:
        return resp.json()["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        raise HTTPException(status_code=502, detail=f"Gemini returned an unexpected response shape: {resp.text[:300]}")


_PROVIDERS = {"groq": _call_groq, "gemini": _call_gemini, "ollama": _call_ollama}


def _is_configured(provider: str) -> bool:
    """Return True if the provider has the credentials it needs to accept a call."""
    if provider == "groq":
        return settings.GROQ_API_KEY not in ("", "your-key-here")
    if provider == "gemini":
        return settings.GEMINI_API_KEY not in ("", "your-key-here")
    return True  # ollama needs no key


def pick_provider(task_type: str, has_document_context: bool = False) -> str:
    """Choose the best provider for a task; fall back to any configured provider with a warning."""
    if has_document_context or task_type == "map_generation":
        preferred = "gemini"   # 1M-token context + 1,500 req/day free — right tool for big inputs
    elif task_type in ("gist", "expand_small"):
        preferred = "groq"     # fastest inference for short prompts
    else:
        preferred = settings.LLM_PROVIDER

    if _is_configured(preferred):
        return preferred

    for fallback in ("gemini", "groq", "ollama"):
        if fallback != preferred and _is_configured(fallback):
            logger.warning(
                "Provider %r not configured for task %r — falling back to %r",
                preferred, task_type, fallback,
            )
            return fallback
    return settings.LLM_PROVIDER


# Who to try when a provider hits its rate limit (ollama is local — it has no rate limits)
_FALLBACK = {"groq": "gemini", "gemini": "groq"}


def _log_llm_call(provider: str, task_type: str, status: str, latency_ms: int) -> None:
    """Record which provider served a request into llm_logs — never let logging break the request itself."""
    try:
        from app.db.session import SessionLocal
        from app.models import LlmLog
        db = SessionLocal()
        try:
            db.add(LlmLog(provider=provider, task_type=task_type, status=status, latency_ms=latency_ms))
            db.commit()
        finally:
            db.close()
    except Exception as exc:
        logger.warning("Could not write llm_logs row: %s", exc)


def _call_llm(messages: list[dict], provider: str | None = None, task_type: str = "unknown") -> str:
    """Send messages to a provider; on HTTP 429/503 retry once with the fallback provider. Logs every request."""
    name = provider or settings.LLM_PROVIDER
    start = time.perf_counter()
    try:
        result = _PROVIDERS.get(name, _call_ollama)(messages)
        _log_llm_call(name, task_type, "ok", int((time.perf_counter() - start) * 1000))
        return result
    except RateLimited as exc:
        alt = _FALLBACK.get(name)
        if not alt or not _is_configured(alt):
            _log_llm_call(name, task_type, "unavailable", int((time.perf_counter() - start) * 1000))
            raise HTTPException(
                status_code=429,
                detail=f"{name} is rate limited or unavailable and no fallback provider is configured. {exc}",
            )
        logger.warning("%s rate limited or unavailable — retrying once with %s", name, alt)
        start2 = time.perf_counter()
        try:
            result = _PROVIDERS[alt](messages)
        except RateLimited as exc2:
            _log_llm_call(alt, task_type, "unavailable", int((time.perf_counter() - start2) * 1000))
            raise HTTPException(
                status_code=429,
                detail=f"Both {name} and {alt} are rate limited or unavailable — wait a minute and try again. {exc2}",
            )
        _log_llm_call(alt, task_type, "ok_after_fallback", int((time.perf_counter() - start2) * 1000))
        return result


# ── JSON extraction ────────────────────────────────────────────────────────────

def _extract_json(text: str) -> dict:
    """Pull the first valid JSON object out of model output, stripping any surrounding prose or markdown."""
    # Strip markdown code fences if the model wrapped the JSON
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        cleaned = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    # Try the whole string first
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Fall back to finding the first { … last } substring
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError:
            pass

    raise ValueError(f"No valid JSON found in model output: {text[:200]!r}")


# ── Public functions ───────────────────────────────────────────────────────────

def generate_concepts(
    topic: str,
    depth: str = "standard",
    parent_label: str | None = None,
    task_type: str = "map_generation",
    has_document_context: bool = False,
) -> ConceptList:
    """Ask the LLM to decompose a topic into 6-8 sub-concepts. Retries once on bad JSON."""
    provider = pick_provider(task_type, has_document_context)
    context = f" (in the context of {parent_label})" if parent_label else ""
    user_msg = f"Topic: {topic}{context}"

    system = _SYSTEM_CONCEPTS.format(depth_rule=_DEPTH_RULE[depth])
    messages = [
        {"role": "system", "content": system},
        {"role": "user",   "content": user_msg},
    ]

    # Attempt 1
    raw = _call_llm(messages, provider, task_type)
    try:
        return ConceptList.model_validate(_extract_json(raw))
    except (ValueError, ValidationError):
        pass

    # Attempt 2 — append the bad reply and send a stricter follow-up
    messages += [
        {"role": "assistant", "content": raw},
        {"role": "user",      "content": _RETRY_MSG},
    ]
    raw2 = _call_llm(messages, provider, task_type)
    try:
        return ConceptList.model_validate(_extract_json(raw2))
    except (ValueError, ValidationError) as exc:
        raise HTTPException(
            status_code=422,
            detail=f"LLM failed to return valid JSON after 2 attempts. Last error: {exc}",
        )


def generate_document_hierarchy(doc_outline: str) -> HierarchyList:
    """Ask the LLM to build a parent-linked concept hierarchy grounded ONLY in the given document outline."""
    provider = pick_provider("map_generation", has_document_context=True)
    messages = [
        {"role": "system", "content": _SYSTEM_DOC_HIERARCHY},
        {"role": "user",   "content": f"DOCUMENT:\n{doc_outline}"},
    ]

    # Attempt 1
    raw = _call_llm(messages, provider, "doc_map_generation")
    try:
        return HierarchyList.model_validate(_extract_json(raw))
    except (ValueError, ValidationError):
        pass

    # Attempt 2 — append the bad reply and send a stricter follow-up
    messages += [
        {"role": "assistant", "content": raw},
        {"role": "user",      "content": _RETRY_MSG},
    ]
    raw2 = _call_llm(messages, provider, "doc_map_generation")
    try:
        return HierarchyList.model_validate(_extract_json(raw2))
    except (ValueError, ValidationError) as exc:
        raise HTTPException(
            status_code=422,
            detail=f"LLM failed to return a valid concept hierarchy after 2 attempts. Last error: {exc}",
        )


def generate_grounded_explanation(label: str, depth: str, excerpts: str) -> str:
    """Explain a concept using ONLY the given document excerpts — replies a fixed sentence when they don't cover it."""
    provider = pick_provider("grounded_explanation", has_document_context=True)
    guide = _DEPTH_EXPLANATION[depth]
    messages = [
        {"role": "system", "content": _SYSTEM_GROUNDED},
        {"role": "user",   "content": (
            f"DOCUMENT EXCERPTS:\n{excerpts}\n\n"
            f"Explain '{label}' — {guide}. Answer only from the excerpts above."
        )},
    ]

    raw = _call_llm(messages, provider, "grounded_explanation").strip()
    if raw:
        return raw

    # Retry once if blank
    messages += [
        {"role": "assistant", "content": raw},
        {"role": "user",      "content": f'Your response was empty. Explain "{label}" from the excerpts, or reply: The document does not cover this.'},
    ]
    raw2 = _call_llm(messages, provider, "grounded_explanation").strip()
    if raw2:
        return raw2

    raise HTTPException(
        status_code=422,
        detail=f"LLM returned empty grounded explanation for '{label}' after 2 attempts.",
    )


def generate_gap_questions(label: str, excerpts: str) -> list[str]:
    """Ask the LLM what a developer would still need answered about a concept, given only these excerpts."""
    provider = pick_provider("gap_check", has_document_context=True)
    messages = [
        {"role": "system", "content": _SYSTEM_GAP_QUESTIONS},
        {"role": "user", "content": f"CONCEPT: {label}\n\nWHAT THE DOCUMENT SAYS:\n{excerpts}"},
    ]

    raw = _call_llm(messages, provider, "gap_check")
    try:
        return GapQuestions.model_validate(_extract_json(raw)).questions
    except (ValueError, ValidationError):
        pass

    messages += [
        {"role": "assistant", "content": raw},
        {"role": "user", "content": _RETRY_GAP_MSG},
    ]
    raw2 = _call_llm(messages, provider, "gap_check")
    try:
        return GapQuestions.model_validate(_extract_json(raw2)).questions
    except (ValueError, ValidationError):
        return []  # gap-check is best-effort — an empty question list just means "nothing flagged here"


def generate_explanation(label: str, depth: str, task_type: str = "gist") -> str:
    """Ask the LLM to explain a single concept at gist / standard / expert depth. Retries once on empty output."""
    provider = pick_provider(task_type)
    guide = _DEPTH_EXPLANATION[depth]
    messages = [
        {"role": "system", "content": _SYSTEM_EXPLANATION},
        {"role": "user",   "content": f'Explain "{label}" — {guide}. Return only the explanation.'},
    ]

    raw = _call_llm(messages, provider, task_type).strip()
    if raw:
        return raw

    # Retry once if blank
    messages += [
        {"role": "assistant", "content": raw},
        {"role": "user",      "content": f'Your response was empty. Explain "{label}" ({guide}).'},
    ]
    raw2 = _call_llm(messages, provider, task_type).strip()
    if raw2:
        return raw2

    raise HTTPException(
        status_code=422,
        detail=f"LLM returned empty explanation for '{label}' at depth '{depth}' after 2 attempts.",
    )
