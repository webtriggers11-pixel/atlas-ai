"""
Evaluation harness — runs the real pipeline (real embeddings, real LLM) on hand-labelled
document pairs and reports retrieval and classification quality.

Usage (from backend/):
    python -m eval.run_eval --label baseline
    python -m eval.run_eval --label hybrid --datasets payments_api clinic_portal
    python -m eval.run_eval --label baseline --retrieval-only     # no LLM calls

Safety: runs ONLY against the test database (same rule as tests/conftest.py) and
deletes the temporary projects it creates.

Metrics
- recall@1 / recall@k / MRR: is the labelled evidence in the retrieved chunks, and how high?
- status accuracy + confusion matrix
- false-missing rate: labelled covered/partial/conflict but predicted missing (the trust killer)
- false-covered rate: labelled missing but predicted covered (an unsupported claim)
- evidence validity: share of model-cited quotes that passed verification
- evidence location: for supported findings, does a cited chunk contain the labelled evidence?
"""
import argparse
import json
import os
import re
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from dotenv import dotenv_values  # noqa: E402
from sqlalchemy.engine import make_url  # noqa: E402


def _configure_env() -> str:
    """Point the app at the TEST database with eager tasks and real embeddings, before importing app."""
    env = dotenv_values(BACKEND / ".env")
    explicit = os.getenv("TEST_DATABASE_URL") or env.get("TEST_DATABASE_URL")
    url = make_url(explicit or env["DATABASE_URL"])
    if not url.database.endswith(("-test", "_test")):
        url = url.set(database=f"{url.database}-test")
    os.environ["DATABASE_URL"] = url.render_as_string(hide_password=False)
    os.environ["CELERY_TASK_ALWAYS_EAGER"] = "true"
    os.environ["AUTO_MIGRATE"] = "false"
    os.environ.setdefault("EMBEDDING_PROVIDER", "local")
    os.environ["UPLOAD_DIR"] = tempfile.mkdtemp(prefix="atlas-eval-")
    return url.database


DATABASE_NAME = _configure_env()

from sqlalchemy import select  # noqa: E402

from app import llm  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models import AgentTrace, Finding, Requirement  # noqa: E402
from app.schemas.project import ProjectCreate  # noqa: E402
from app.services import analysis_service, ingestion_service, investigator, project_service  # noqa: E402
from app.services.requirement_service import requirement_hash  # noqa: E402

DATASETS = Path(__file__).parent / "datasets"
RESULTS = Path(__file__).parent / "results"
REPORT = BACKEND.parent / "idea-atlas-docs" / "v2" / "EVAL_RESULTS.md"
STATUSES = ["covered", "partial", "missing", "conflict", "unclear"]
SUPPORTED = ("covered", "partial", "conflict")


def _norm(text: str) -> str:
    """Lowercase and collapse whitespace for substring checks."""
    return re.sub(r"\s+", " ", text).strip().lower()


def _contains(chunk_text: str, expected: str) -> bool:
    """Does a chunk contain the labelled evidence snippet?"""
    return _norm(expected) in _norm(chunk_text)


def evaluate_dataset(name: str, retrieval_only: bool, investigate: bool = False) -> dict:
    """Ingest one dataset into a temporary project, run retrieval (+ analysis) and score it."""
    labels = json.loads((DATASETS / name / "labels.json").read_text(encoding="utf-8"))
    db = SessionLocal()
    project_id = None
    try:
        project = project_service.create_project(ProjectCreate(name=f"eval:{name}", preset=labels["preset"]), db)
        project_id = project.id
        for role in ("reference", "existing"):
            data = (DATASETS / name / f"{role}.md").read_bytes()
            doc, _ = ingestion_service.upload_document(project_id, role, f"{role}.md", data, db)
            db.refresh(doc)
            if doc.status != "indexed":
                raise RuntimeError(f"{name}/{role}.md failed to index: {doc.error_message}")

        reqs = {}
        for item in labels["requirements"]:
            r = Requirement(project_id=project_id, code=item["id"], text=item["text"], status="approved",
                            origin="manual", content_hash=requirement_hash(item["text"]))
            db.add(r)
            reqs[item["id"]] = r
        db.commit()

        rows = []
        retrieval_stats: dict = {}
        all_hits = analysis_service.retrieve_for_requirements(project_id, list(reqs.values()), db, retrieval_stats)
        for item in labels["requirements"]:
            hits = all_hits[reqs[item["id"]].id]
            rank = next((h.rank for h in hits if item["evidence"] and _contains(h.chunk.content, item["evidence"])), None)
            rows.append({"id": item["id"], "expected": item["expected_status"], "evidence": item["evidence"],
                         "rank": rank, "top_score": round(hits[0].score, 3) if hits else None})

        run_stats = {}
        if not retrieval_only:
            run = analysis_service.start_analysis(project_id, db)
            db.refresh(run)
            run_stats = dict(run.stats or {}, status=run.status, error=run.error_message, model=run.model)
            def _statuses():
                """Current finding status per labelled requirement id."""
                db.expire_all()
                current = {f.requirement_id: f.status for f in db.execute(select(Finding).where(Finding.run_id == run.id)).scalars()}
                return {row["id"]: current.get(reqs[row["id"]].id) for row in rows}

            if investigate:
                before = _statuses()
                traces = investigator.start_run_investigation(run.id, db)   # inline (eager) — returns when done
                db.expire_all()
                done = [db.get(AgentTrace, t.id) for t in traces]
                run_stats["agent"] = {
                    "investigated": len(done),
                    "outcomes": {o: sum(1 for t in done if t.outcome == o) for o in ("changed", "confirmed", "rejected", "no_verdict", "error")},
                    "tool_calls": sum(t.tool_calls for t in done),
                }
                for row in rows:
                    row["predicted_before_agent"] = before[row["id"]]

            findings = db.execute(select(Finding).where(Finding.run_id == run.id)).scalars().all()
            by_req = {f.requirement_id: f for f in findings}
            for row in rows:
                f = by_req.get(reqs[row["id"]].id)
                row["predicted"] = f.status if f else None
                row["confidence"] = f.confidence if f else None
                row["explanation"] = f.explanation if f else None
                row["evidence_ok"] = (
                    any(_contains(e.chunk.content, row["evidence"]) for e in f.evidence)
                    if f and row["evidence"] and f.status in SUPPORTED else None
                )
                row["evidence_count"] = len(f.evidence) if f else 0
        return {"dataset": name, "preset": labels["preset"], "rows": rows, "run": run_stats, "retrieval": retrieval_stats}
    finally:
        if project_id is not None:
            db.rollback()
            project_service.delete_project(project_id, db)
        db.close()


def summarize(results: list[dict], k: int, retrieval_only: bool) -> dict:
    """Aggregate per-requirement rows into the headline metrics."""
    rows = [r for res in results for r in res["rows"]]
    with_evidence = [r for r in rows if r["evidence"]]
    m = {
        "requirements": len(rows),
        "recall@1": sum(1 for r in with_evidence if r["rank"] == 1) / len(with_evidence),
        f"recall@{k}": sum(1 for r in with_evidence if r["rank"]) / len(with_evidence),
        "mrr": sum(1 / r["rank"] for r in with_evidence if r["rank"]) / len(with_evidence),
    }
    m["rewrite_calls"] = sum(res["retrieval"].get("rewrite_calls", 0) for res in results)
    if retrieval_only:
        return m

    scored = [r for r in rows if r.get("predicted")]
    supported = [r for r in scored if r["expected"] in SUPPORTED]
    missing = [r for r in scored if r["expected"] == "missing"]
    ev_checked = [r for r in scored if r["evidence_ok"] is not None]
    kept = sum(r["evidence_count"] for r in scored)
    dropped = sum(res["run"].get("evidence_dropped", 0) for res in results)
    m.update({
        "status_accuracy": sum(1 for r in scored if r["predicted"] == r["expected"]) / len(scored),
        "false_missing_rate": sum(1 for r in supported if r["predicted"] == "missing") / len(supported),
        "false_covered_rate": sum(1 for r in missing if r["predicted"] == "covered") / max(1, len(missing)),
        "unclear_rate": sum(1 for r in scored if r["predicted"] == "unclear") / len(scored),
        "evidence_validity": kept / (kept + dropped) if kept + dropped else 1.0,
        "evidence_location": sum(1 for r in ev_checked if r["evidence_ok"]) / max(1, len(ev_checked)),
        "llm_calls": sum(res["run"].get("llm_calls", 0) for res in results),
        "seconds_per_requirement": sum(res["run"].get("duration_s", 0) for res in results) / len(rows),
        "model": results[0]["run"].get("model"),
    })
    if any("predicted_before_agent" in r for r in scored):
        m["status_accuracy_before_agent"] = sum(1 for r in scored if r.get("predicted_before_agent") == r["expected"]) / len(scored)
        before_supported = [r for r in supported if r.get("predicted_before_agent")]
        m["false_missing_before_agent"] = sum(1 for r in before_supported if r["predicted_before_agent"] == "missing") / max(1, len(before_supported))
        agent = [res["run"].get("agent", {}) for res in results]
        m["agent_investigated"] = sum(a.get("investigated", 0) for a in agent)
        m["agent_changed"] = sum(a.get("outcomes", {}).get("changed", 0) for a in agent)
        m["agent_rejected"] = sum(a.get("outcomes", {}).get("rejected", 0) for a in agent)
        m["agent_tool_calls"] = sum(a.get("tool_calls", 0) for a in agent)
    confusion = {e: {p: 0 for p in STATUSES} for e in STATUSES}
    for r in scored:
        confusion[r["expected"]][r["predicted"]] += 1
    m["confusion"] = confusion
    return m


def _pct(x: float) -> str:
    """Format a ratio as a percentage."""
    return f"{x * 100:.0f}%"


def write_report(label: str, metrics: dict, results: list[dict], k: int, retrieval_only: bool) -> Path:
    """Save full JSON results and append a summary row (plus misclassifications) to EVAL_RESULTS.md."""
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    RESULTS.mkdir(exist_ok=True)
    out = RESULTS / f"{datetime.now(timezone.utc):%Y%m%d_%H%M%S}_{label}.json"
    out.write_text(json.dumps({"label": label, "at": stamp, "metrics": metrics, "results": results,
                               "settings": {"retrieval_mode": settings.RETRIEVAL_MODE, "k": k,
                                            "query_rewrite": settings.QUERY_REWRITE,
                                            "prompt": llm.PROMPT_VERSIONS, "embedding": settings.EMBEDDING_MODEL}},
                              indent=2, default=str), encoding="utf-8")

    if not REPORT.exists():
        REPORT.write_text(
            "# Evaluation results\n\nGenerated by `python -m eval.run_eval`. Datasets: `backend/eval/datasets/` "
            "(small, synthetic, hand-labelled — numbers are indicative, not statistically strong).\n\n"
            "| When | Label | Retrieval | Model | Reqs | Recall@1 | Recall@k | MRR | Status acc. | False-missing | "
            "False-covered | Unclear | Evidence valid | Evidence location | LLM calls | s/req |\n"
            "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n", encoding="utf-8")

    if retrieval_only:
        row = (f"| {stamp} | {label} | {settings.RETRIEVAL_MODE} k={k} | — | {metrics['requirements']} | "
               f"{_pct(metrics['recall@1'])} | {_pct(metrics[f'recall@{k}'])} | {metrics['mrr']:.2f} | — | — | — | — | — | — | "
               f"{metrics['rewrite_calls']} | — |\n")
    else:
        row = (f"| {stamp} | {label} | {settings.RETRIEVAL_MODE} k={k} | {metrics['model']} | {metrics['requirements']} | "
               f"{_pct(metrics['recall@1'])} | {_pct(metrics[f'recall@{k}'])} | {metrics['mrr']:.2f} | "
               f"{_pct(metrics['status_accuracy'])} | {_pct(metrics['false_missing_rate'])} | "
               f"{_pct(metrics['false_covered_rate'])} | {_pct(metrics['unclear_rate'])} | "
               f"{_pct(metrics['evidence_validity'])} | {_pct(metrics['evidence_location'])} | "
               f"{metrics['llm_calls'] + metrics['rewrite_calls']} | {metrics['seconds_per_requirement']:.1f} |\n")
    content = REPORT.read_text(encoding="utf-8")
    marker = "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n"
    head, tail = content.split(marker, 1)
    table_rows, rest = [], tail
    lines = tail.splitlines(keepends=True)
    i = 0
    while i < len(lines) and lines[i].startswith("|"):
        table_rows.append(lines[i])
        i += 1
    rest = "".join(lines[i:])
    REPORT.write_text(head + marker + "".join(table_rows) + row + rest, encoding="utf-8")
    return out


def main():
    """CLI entry point."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # Windows consoles default to cp1252
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--label", required=True, help="name for this run, e.g. baseline or hybrid")
    parser.add_argument("--datasets", nargs="*", default=sorted(p.name for p in DATASETS.iterdir() if p.is_dir()))
    parser.add_argument("--k", type=int, default=None, help="evidence chunks per requirement (default EVIDENCE_K)")
    parser.add_argument("--retrieval-only", action="store_true", help="skip LLM classification")
    parser.add_argument("--investigate", action="store_true", help="run the investigator agent on uncertain findings and score before/after")
    args = parser.parse_args()
    k = args.k or settings.EVIDENCE_K
    settings.EVIDENCE_K = k

    print(f"Evaluating {args.datasets} on database {DATABASE_NAME!r} (retrieval={settings.RETRIEVAL_MODE}, k={k})")
    started = time.perf_counter()
    results = []
    for name in args.datasets:
        t = time.perf_counter()
        res = evaluate_dataset(name, args.retrieval_only, args.investigate)
        results.append(res)
        print(f"  {name}: {len(res['rows'])} requirements in {time.perf_counter() - t:.0f}s "
              f"{'' if args.retrieval_only else '(run ' + str(res['run'].get('status')) + ')'}")

    metrics = summarize(results, k, args.retrieval_only)
    out = write_report(args.label, metrics, results, k, args.retrieval_only)

    print("\nMetrics:")
    for key, value in metrics.items():
        if key != "confusion":
            print(f"  {key:26s} {value:.3f}" if isinstance(value, float) else f"  {key:26s} {value}")
    if "confusion" in metrics:
        print("\nConfusion (rows = expected, cols = predicted):")
        print("  " + " ".join(f"{s[:8]:>9s}" for s in ["", *STATUSES]))
        for e, preds in metrics["confusion"].items():
            print("  " + f"{e[:8]:>9s} " + " ".join(f"{preds[p]:>9d}" for p in STATUSES))
        if args.investigate:
            print("\nAgent changes (expected · before → after):")
            for res in results:
                for r in res["rows"]:
                    if r.get("predicted_before_agent") and r["predicted_before_agent"] != r.get("predicted"):
                        mark = "fixed" if r["predicted"] == r["expected"] else ("broke" if r["predicted_before_agent"] == r["expected"] else "changed")
                        print(f"  {r['id']}: {r['expected']} · {r['predicted_before_agent']} → {r['predicted']}  [{mark}]")
        print("\nMisclassified:")
        for res in results:
            for r in res["rows"]:
                if r.get("predicted") and r["predicted"] != r["expected"]:
                    print(f"  {r['id']}: expected {r['expected']}, got {r['predicted']} — {(r['explanation'] or '')[:150]}")
    print(f"\nSaved {out.relative_to(BACKEND)} and updated {REPORT.name} in {time.perf_counter() - started:.0f}s")


if __name__ == "__main__":
    main()
