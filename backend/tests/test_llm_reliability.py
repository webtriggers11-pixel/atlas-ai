"""
V2 Phase 8 — LLM reliability: fallback, cooldowns, bounded backoff, non-retryable errors, token logging.
HTTP is faked (no real API calls) and time.sleep is captured, so tests are fast and deterministic.
Run from backend/: pytest tests/test_llm_reliability.py -v
"""
from unittest.mock import patch

import httpx
import pytest
from fastapi import HTTPException

from app import llm
from app.core.config import settings

GROQ_OK = {"choices": [{"message": {"content": "groq answer"}}], "usage": {"prompt_tokens": 120, "completion_tokens": 30}}
GEMINI_OK = {"candidates": [{"content": {"parts": [{"text": "gemini answer"}]}}],
             "usageMetadata": {"promptTokenCount": 200, "candidatesTokenCount": 40}}


@pytest.fixture(autouse=True)
def clean_state(monkeypatch):
    """Fresh cooldowns, both providers configured, deterministic jitter, no DB logging."""
    llm._cooldown_until.clear()
    monkeypatch.setattr(settings, "GROQ_API_KEY", "test-key")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(settings, "LLM_MAX_ATTEMPTS", 4)
    monkeypatch.setattr(llm.random, "uniform", lambda a, b: 0.0)
    yield
    llm._cooldown_until.clear()


class FakeHTTP:
    """Scripted httpx.post: a queue of responses (or exceptions) per provider."""

    def __init__(self, groq=(), gemini=()):
        """Store the scripted replies."""
        self.script = {"groq": list(groq), "gemini": list(gemini)}
        self.calls = []

    def __call__(self, url, timeout=None, **kwargs):
        """Return (or raise) the next scripted reply for whichever provider the URL belongs to."""
        provider = "groq" if "groq.com" in url else "gemini"
        self.calls.append(provider)
        reply = self.script[provider].pop(0)
        if isinstance(reply, Exception):
            raise reply
        status, body, headers = reply
        if isinstance(body, dict):
            return httpx.Response(status, json=body, headers=headers or {})
        return httpx.Response(status, text=body, headers=headers or {})


def _run(fake, provider="gemini", budget=20, logs=None):
    """Call _call_llm with fake HTTP, captured sleeps and captured log rows."""
    sleeps = []
    logs = logs if logs is not None else []
    with patch("app.llm.httpx.post", side_effect=fake), \
         patch("app.llm.time.sleep", side_effect=sleeps.append), \
         patch("app.llm._log_llm_call", side_effect=lambda *a, **k: logs.append((a, k))):
        text = llm._call_llm([{"role": "user", "content": "hi"}], provider, "classify_requirements", retry_budget_s=budget)
    return text, sleeps, logs


def test_rate_limit_falls_back_and_sets_cooldown():
    """429 on Gemini → immediate fallback to Groq, and Gemini is put on cooldown for its retry-after."""
    fake = FakeHTTP(gemini=[(429, "quota", {"retry-after": "30"})], groq=[(200, GROQ_OK, None)])
    text, sleeps, logs = _run(fake)
    assert text == "groq answer" and fake.calls == ["gemini", "groq"] and sleeps == []
    assert llm._cooldown_until["gemini"] > llm.time.monotonic() + 25
    statuses = [a[2] for a, _ in logs]
    assert statuses == ["rate_limited", "ok_after_retry"]


def test_cooldown_skips_provider_on_next_call():
    """While Gemini is cooling down, the next call goes straight to Groq (no wasted request)."""
    _run(FakeHTTP(gemini=[(429, "quota", {"retry-after": "30"})], groq=[(200, GROQ_OK, None)]))
    fake = FakeHTTP(groq=[(200, GROQ_OK, None)])
    text, _, _ = _run(fake)
    assert text == "groq answer" and fake.calls == ["groq"]


GEMINI_DAILY = ('{"error": {"code": 429, "message": "You exceeded your current quota", "details": [{"violations": '
                '[{"quotaId": "GenerateRequestsPerDayPerProjectPerModel-FreeTier"}]}, {"retryDelay": "20s"}]}}')


def test_daily_quota_cools_down_for_an_hour_not_a_minute():
    """Gemini's DAILY quota → long cooldown (not its 20s retryDelay), so later calls go straight to Groq."""
    fake = FakeHTTP(gemini=[(429, GEMINI_DAILY, None)], groq=[(200, GROQ_OK, None), (200, GROQ_OK, None)])
    text, sleeps, _ = _run(fake)
    assert text == "groq answer" and sleeps == []
    assert llm._cooldown_until["gemini"] > llm.time.monotonic() + 3000
    _run(fake)                                         # next call: Gemini isn't even tried
    assert fake.calls == ["gemini", "groq", "groq"]


def test_daily_quota_plus_busy_provider_fails_fast_with_clear_message():
    """Gemini out for the day and Groq per-minute limited → fail without long waits and say why."""
    fake = FakeHTTP(gemini=[(429, GEMINI_DAILY, None)], groq=[(429, "Rate limit reached for tokens per minute (TPM)",
                                                                   {"retry-after": "50"})])
    with pytest.raises(HTTPException) as err:
        _run(fake, budget=20)
    assert err.value.status_code == 429
    assert "Daily free AI quota used up for gemini" in err.value.detail and "groq is busy" in err.value.detail


def test_groq_daily_token_limit_detected():
    """Groq's 'tokens per day (TPD)' 429 counts as a daily quota."""
    fake = FakeHTTP(gemini=[(200, GEMINI_OK, None)],
                    groq=[(429, "Rate limit reached for model on tokens per day (TPD): Limit 200000", None)])
    text, _, _ = _run(fake, provider="groq")
    assert text == "gemini answer" and llm._cooldown_until["groq"] > llm.time.monotonic() + 3000


def test_both_rate_limited_waits_then_succeeds():
    """Both providers 429 with short retry-after → one bounded wait, then success."""
    fake = FakeHTTP(
        gemini=[(429, '{"error": {"details": [{"retryDelay": "3s"}]}}', None), (200, GEMINI_OK, None)],
        groq=[(429, "slow down", {"retry-after": "4"})],
    )
    text, sleeps, _ = _run(fake)
    assert text == "gemini answer"
    assert fake.calls == ["gemini", "groq", "gemini"]
    assert len(sleeps) == 1 and 2.5 < sleeps[0] <= 3.1      # waited for Gemini's 3s retryDelay (the soonest)


def test_budget_exhausted_raises_429_without_long_sleep():
    """If the providers ask for longer than the retry budget, fail fast with a clear 429."""
    fake = FakeHTTP(gemini=[(429, "quota", {"retry-after": "50"})], groq=[(429, "quota", {"retry-after": "50"})])
    with pytest.raises(HTTPException) as err:
        _run(fake, budget=20)
    assert err.value.status_code == 429 and "rate limited" in err.value.detail


def test_timeout_is_transient_and_falls_back():
    """A timeout on one provider is retried on the other."""
    fake = FakeHTTP(gemini=[httpx.ReadTimeout("slow")], groq=[(200, GROQ_OK, None)])
    text, _, logs = _run(fake)
    assert text == "groq answer" and [a[2] for a, _ in logs] == ["unavailable", "ok_after_retry"]


def test_bad_request_is_not_retried():
    """A 400 (our bug or bad key) is not transient: no fallback, no retry, immediate 502."""
    fake = FakeHTTP(gemini=[(400, "invalid argument", None)], groq=[(200, GROQ_OK, None)])
    with pytest.raises(HTTPException) as err:
        _run(fake)
    assert err.value.status_code == 502 and fake.calls == ["gemini"]


def test_token_usage_is_parsed_and_logged():
    """Prompt/completion tokens from the provider's usage block reach the log row."""
    fake = FakeHTTP(gemini=[(200, GEMINI_OK, None)])
    _, _, logs = _run(fake)
    result = logs[0][0][4]
    assert (result.prompt_tokens, result.completion_tokens) == (200, 40)


def test_call_context_tags_calls():
    """call_context sets the job reference seen by the logger, and resets afterwards."""
    with llm.call_context("run:abc"):
        assert llm._call_context.get() == "run:abc"
    assert llm._call_context.get() is None


def test_llm_calls_row_written(migrated):
    """The real logger writes a row with tokens and context into llm_calls (test database)."""
    from sqlalchemy import select
    from app.db.session import SessionLocal
    from app.models import LlmCall

    with llm.call_context("test:logging"):
        llm._log_llm_call("groq", "classify_requirements", "ok", 123, llm.LLMResult("x", 10, 5))
    db = SessionLocal()
    try:
        row = db.execute(select(LlmCall).where(LlmCall.context == "test:logging").order_by(LlmCall.created_at.desc())).scalars().first()
        assert (row.prompt_tokens, row.completion_tokens, row.latency_ms, row.prompt_version) == (10, 5, 123, settings.CLASSIFY_PROMPT)
        db.delete(row)
        db.commit()
    finally:
        db.close()


def test_prompt_v2_selected_by_setting():
    """classify-v2 rules (ordered decision list) are what the classifier sends."""
    captured = {}

    def fake_call(messages, provider, task_type, max_tokens=None, json_mode=False, retry_budget_s=None):
        """Capture the system prompt and answer validly."""
        captured["system"] = messages[0]["content"]
        return '{"results":[{"id":"R1","status":"partial","confidence":0.6,"explanation":"Not stated.","evidence":[]}]}'

    with patch("app.llm._call_llm", side_effect=fake_call), patch("app.llm.pick_provider", return_value="groq"):
        llm.classify_requirements([{"id": "R1", "text": "t"}], [])
    assert "taking the FIRST that applies" in captured["system"]
    assert "Never answer missing when an excerpt talks about the same feature" in captured["system"]


def test_invalid_output_twice_falls_back_to_other_provider():
    """Two invalid answers from the preferred provider → a fresh attempt on the other provider succeeds."""
    replies = {"gemini": ['{"results": "nope"}', '{"results": "still nope"}'],
               "groq": ['{"requirements":[{"text":"The system must log errors.","section":null}]}']}
    used, logged = [], []

    def fake_call(messages, provider, task_type, **kwargs):
        """Reply per provider in order."""
        used.append(provider)
        return replies[provider].pop(0)

    with patch("app.llm._call_llm", side_effect=fake_call), patch("app.llm.pick_provider", return_value="gemini"), \
         patch("app.llm._log_llm_call", side_effect=lambda *a, **k: logged.append(k.get("error", ""))):
        result = llm.extract_requirements("<section>Errors must be logged.</section>")
    assert result[0].text == "The system must log errors."
    assert used == ["gemini", "gemini", "groq"]
    assert len(logged) == 2 and all("raw output not stored" in e for e in logged)   # document text not logged by default


def test_invalid_output_raw_text_logged_only_when_enabled(monkeypatch):
    """LOG_LLM_RAW_OUTPUT=true keeps the raw invalid output for debugging."""
    monkeypatch.setattr(llm.settings, "LOG_LLM_RAW_OUTPUT", True)
    replies = ['{"results": "nope"}', '{"requirements":[{"text":"The system must log errors.","section":null}]}']
    logged = []
    with patch("app.llm._call_llm", side_effect=lambda *a, **k: replies.pop(0)),          patch("app.llm.pick_provider", return_value="gemini"),          patch("app.llm._log_llm_call", side_effect=lambda *a, **k: logged.append(k.get("error", ""))):
        llm.extract_requirements("<section>Errors must be logged.</section>")
    assert len(logged) == 1 and 'raw: {"results": "nope"}' in logged[0]


def test_groq_json_validate_failed_is_retried_elsewhere():
    """Groq 400 json_validate_failed is a bad generation, not a bad request → fall back to the other provider."""
    fake = FakeHTTP(groq=[(400, '{"error":{"code":"json_validate_failed"}}', None)], gemini=[(200, GEMINI_OK, None)])
    text, _, _ = _run(fake, provider="groq")
    assert text == "gemini answer" and fake.calls == ["groq", "gemini"]
    assert "groq" not in llm._cooldown_until           # no cooldown: the provider itself is healthy


def test_one_malformed_result_does_not_discard_the_batch():
    """A list with one non-object item keeps the valid results."""
    parsed = llm.ClassificationList.model_validate({"results": [
        {"id": "R1", "status": "covered", "confidence": 0.9, "explanation": "Stated.", "evidence": []},
        "garbage",
        {"id": "R3", "status": "missing", "confidence": 0.8, "explanation": "Not stated.", "evidence": []},
    ]})
    assert [r.id for r in parsed.results] == ["R1", "R3"]
