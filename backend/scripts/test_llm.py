"""
Phase 2 verification — runs generate_concepts across multiple topics and tests all 3 depth levels.
Usage (from backend/ with venv active):
    python scripts/test_llm.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.llm import generate_concepts, generate_explanation

TOPICS = [
    "machine learning",
    "the French Revolution",
    "quantum computing",
    "photosynthesis",
    "the TCP/IP protocol",
]

def run():
    passed = 0
    failed = 0

    # ── Test generate_concepts ────────────────────────────────────────────────
    for topic in TOPICS:
        print(f"\n{'─'*55}")
        print(f"  Topic: {topic}")
        print(f"{'─'*55}")
        try:
            result = generate_concepts(topic, depth="standard")
            print(f"  [OK] {len(result.concepts)} concepts:")
            for c in result.concepts:
                print(f"    • {c.label}")
                print(f"      {c.summary[:80]}{'...' if len(c.summary) > 80 else ''}")
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {e}")
            failed += 1

    # ── Test expand (parent_label context) ───────────────────────────────────
    print(f"\n{'─'*55}")
    print("  Expand: 'Attention mechanism' inside 'Transformers in AI'")
    print(f"{'─'*55}")
    try:
        result = generate_concepts(
            topic="Attention mechanism",
            depth="standard",
            parent_label="Transformers in AI",
        )
        print(f"  [OK] {len(result.concepts)} sub-concepts:")
        for c in result.concepts:
            print(f"    • {c.label}")
        passed += 1
    except Exception as e:
        print(f"  [FAIL] {e}")
        failed += 1

    # ── Test depth toggle ─────────────────────────────────────────────────────
    print(f"\n{'─'*55}")
    print("  Depth toggle: 'Neural networks'")
    print(f"{'─'*55}")
    for depth in ["gist", "standard", "expert"]:
        try:
            text = generate_explanation("Neural networks", depth)
            print(f"\n  [{depth.upper()}]")
            print(f"  {text[:140]}{'...' if len(text) > 140 else ''}")
            passed += 1
        except Exception as e:
            print(f"\n  [FAIL {depth}] {e}")
            failed += 1

    # ── Summary ───────────────────────────────────────────────────────────────
    total = passed + failed
    print(f"\n{'═'*55}")
    print(f"  {passed}/{total} passed  {'✓ Phase 2 complete' if failed == 0 else '✗ fix failures above'}")
    print(f"{'═'*55}\n")


if __name__ == "__main__":
    run()
