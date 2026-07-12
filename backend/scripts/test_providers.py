"""
Phase A test script — verifies both cloud providers respond and the 429 fallback works.
Run from the backend folder:  python scripts/test_providers.py
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from app import llm
from app.llm import _call_groq, _call_gemini, _call_llm, RateLimited

PROMPT = [{"role": "user", "content": "Name one interesting fact about the moon in one sentence."}]


def timed(name: str, fn) -> None:
    """Run one provider call and print its name, latency, and the first 100 chars of the reply."""
    start = time.perf_counter()
    reply = fn(PROMPT)
    ms = int((time.perf_counter() - start) * 1000)
    print(f"[{name:8}] {ms:5} ms -> {reply[:100]!r}")


def fake_rate_limited(messages: list[dict]) -> str:
    """Stand-in for Groq that always reports a rate limit — lets us test fallback without real 429s."""
    raise RateLimited("simulated 429 for testing")


if __name__ == "__main__":
    print("-- direct provider calls --")
    timed("groq", _call_groq)
    timed("gemini", _call_gemini)

    print("\n-- 429 fallback test (groq simulated as rate-limited) --")
    original = llm._PROVIDERS["groq"]
    llm._PROVIDERS["groq"] = fake_rate_limited
    try:
        start = time.perf_counter()
        reply = _call_llm(PROMPT, provider="groq", task_type="fallback_test")
        ms = int((time.perf_counter() - start) * 1000)
        print(f"[fallback] groq hit 429 -> gemini served it in {ms} ms -> {reply[:100]!r}")
    finally:
        llm._PROVIDERS["groq"] = original

    print("\nAll Phase A checks passed.")
