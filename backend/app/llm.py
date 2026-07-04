"""
All LLM calls live here and ONLY here.
Switching providers (ollama ↔ groq) means editing only this file — nothing else changes.
"""
import json
import httpx
from pydantic import BaseModel, ValidationError
from fastapi import HTTPException
from app.core.config import settings


# ── Response shape ────────────────────────────────────────────────────────────

class Concept(BaseModel):
    label: str
    summary: str


class ConceptList(BaseModel):
    concepts: list[Concept]


# ── Prompt templates ──────────────────────────────────────────────────────────

_DEPTH_RULE = {
    "gist":     "Each summary: ONE sentence, under 15 words, plain everyday language.",
    "standard": "Each summary: ONE clear sentence, accessible to a curious non-expert.",
    "expert":   "Each summary: ONE precise technical sentence using domain terminology.",
}

# Few-shot system prompt — the worked example is the key trick for small models
_SYSTEM_CONCEPTS = """\
You are a concept decomposition engine. Your ONLY output is a single JSON object — \
no introduction, no explanation, no markdown, nothing before or after the JSON.

Return exactly 6-8 sub-concepts for the given topic in this format:
{{
  "concepts": [
    {{"label": "Short concept name", "summary": "One sentence."}},
    {{"label": "Short concept name", "summary": "One sentence."}}
  ]
}}

Rules:
- label: 2-5 words
- summary: {depth_rule}
- Output ONLY the JSON. If you write anything else the output is invalid.

Worked example — input: "machine learning"
Output:
{{
  "concepts": [
    {{"label": "Supervised learning", "summary": "Training a model on labeled examples so it predicts correct outputs on new data."}},
    {{"label": "Neural networks", "summary": "Layers of connected functions that learn patterns by adjusting internal weights during training."}},
    {{"label": "Gradient descent", "summary": "An algorithm that iteratively nudges model parameters in the direction that reduces prediction error."}},
    {{"label": "Overfitting", "summary": "When a model memorises training data so closely that it fails to generalise to unseen examples."}},
    {{"label": "Feature engineering", "summary": "Transforming raw data into meaningful inputs that help a model learn more effectively."}},
    {{"label": "Cross-validation", "summary": "Evaluating a model by training and testing it on different subsets of data to estimate real-world performance."}}
  ]
}}\
"""

# Sent as a follow-up user message when attempt 1 returns bad JSON
_RETRY_MSG = """\
Your previous response was not valid JSON. This is your only retry.

Return ONLY this structure — nothing before it, nothing after it:
{{"concepts": [{{"label": "...", "summary": "..."}}, ...]}}\
"""

_SYSTEM_EXPLANATION = """\
You are a technical explainer. Return ONLY plain prose — no JSON, no markdown, \
no bullet points, no headers, nothing except the explanation itself.\
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
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Ollama error {resp.status_code}: {resp.text}")
    return resp.json()["message"]["content"]


def _call_groq(messages: list[dict]) -> str:
    """POST to Groq /chat/completions (OpenAI-compatible) and return the assistant message text."""
    try:
        resp = httpx.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
            json={"model": settings.GROQ_MODEL, "messages": messages, "temperature": 0.3},
            timeout=30.0,
        )
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Cannot reach Groq API. Check your network.")
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Groq error {resp.status_code}: {resp.text}")
    return resp.json()["choices"][0]["message"]["content"]


def _call_llm(messages: list[dict]) -> str:
    """Route to Ollama or Groq based on LLM_PROVIDER — the only branching on provider in the codebase."""
    if settings.LLM_PROVIDER == "groq":
        return _call_groq(messages)
    return _call_ollama(messages)


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
) -> ConceptList:
    """Ask the LLM to decompose a topic into 6-8 sub-concepts. Retries once on bad JSON."""
    context = f" (in the context of {parent_label})" if parent_label else ""
    user_msg = f"Topic: {topic}{context}"

    system = _SYSTEM_CONCEPTS.format(depth_rule=_DEPTH_RULE[depth])
    messages = [
        {"role": "system", "content": system},
        {"role": "user",   "content": user_msg},
    ]

    # Attempt 1
    raw = _call_llm(messages)
    try:
        return ConceptList.model_validate(_extract_json(raw))
    except (ValueError, ValidationError):
        pass

    # Attempt 2 — append the bad reply and send a stricter follow-up
    messages += [
        {"role": "assistant", "content": raw},
        {"role": "user",      "content": _RETRY_MSG},
    ]
    raw2 = _call_llm(messages)
    try:
        return ConceptList.model_validate(_extract_json(raw2))
    except (ValueError, ValidationError) as exc:
        raise HTTPException(
            status_code=422,
            detail=f"LLM failed to return valid JSON after 2 attempts. Last error: {exc}",
        )


def generate_explanation(label: str, depth: str) -> str:
    """Ask the LLM to explain a single concept at gist / standard / expert depth. Retries once on empty output."""
    guide = _DEPTH_EXPLANATION[depth]
    messages = [
        {"role": "system", "content": _SYSTEM_EXPLANATION},
        {"role": "user",   "content": f'Explain "{label}" — {guide}. Return only the explanation.'},
    ]

    raw = _call_llm(messages).strip()
    if raw:
        return raw

    # Retry once if blank
    messages += [
        {"role": "assistant", "content": raw},
        {"role": "user",      "content": f'Your response was empty. Explain "{label}" ({guide}).'},
    ]
    raw2 = _call_llm(messages).strip()
    if raw2:
        return raw2

    raise HTTPException(
        status_code=422,
        detail=f"LLM returned empty explanation for '{label}' at depth '{depth}' after 2 attempts.",
    )
