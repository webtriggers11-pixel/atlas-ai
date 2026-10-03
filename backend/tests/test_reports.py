"""
V2 Phase 11 — report JSON, CSV/Markdown/PDF exports, run diff.
Run from backend/: pytest tests/test_reports.py -v
"""
from datetime import datetime, timedelta, timezone

from app.models import AnalysisRun, Finding, Requirement


def _analysis(client, db):
    """Analysis with three requirements and two completed runs (older and newer)."""
    pid = client.post("/api/v1/projects", json={"name": "Report — test / 1"}).json()["id"]
    reqs = [Requirement(project_id=pid, code=f"REQ-00{i}", text=t, content_hash=str(i), status="approved")
            for i, t in enumerate(["Tokens expire in 15 minutes.", "Audit log is kept 7 years.", "Supports “SSO” login."], start=1)]
    now = datetime.now(timezone.utc)
    old = AnalysisRun(project_id=pid, status="completed", created_at=now - timedelta(hours=1), finished_at=now - timedelta(hours=1))
    new = AnalysisRun(project_id=pid, status="completed", created_at=now, finished_at=now, model="groq/x", prompt_version="classify-v2")
    db.add_all(reqs + [old, new])
    db.flush()
    for run, statuses in ((old, ["missing", "missing", "covered"]), (new, ["covered", "missing", "partial"])):
        for req, st in zip(reqs, statuses):
            db.add(Finding(run_id=run.id, requirement_id=req.id, status=st, explanation=f"{st} — explanation",
                           suggested_action=None if st == "covered" else "Document it."))
    db.flush()
    return pid, old, new


def test_report_structure(client, db):
    """Headline, counts and sections come from the findings; actions skip covered items."""
    _, _, new = _analysis(client, db)
    report = client.get(f"/api/v1/runs/{new.id}/report").json()
    assert report["summary"]["counts"] == {"covered": 1, "partial": 1, "unclear": 0, "conflict": 0, "missing": 1}
    assert report["summary"]["headline"].startswith("1 of 3 requirements (33%) are fully covered")
    assert [r["code"] for r in report["sections"]["missing"]] == ["REQ-002"]
    assert {a["code"] for a in report["actions"]} == {"REQ-002", "REQ-003"}


def test_exports_csv_markdown_pdf(client, db):
    """All three formats download with the right type and a safe filename; PDF survives Unicode text."""
    _, _, new = _analysis(client, db)
    csv_resp = client.get(f"/api/v1/runs/{new.id}/export?format=csv")
    assert csv_resp.headers["content-type"].startswith("text/csv")
    assert 'filename="Report-test-1-report.csv"' in csv_resp.headers["content-disposition"]
    assert csv_resp.text.splitlines()[0].startswith("Code,Requirement,Section,Status")
    assert "REQ-002" in csv_resp.text

    md = client.get(f"/api/v1/runs/{new.id}/export?format=md").text
    assert "## Executive summary" in md and "## Missing areas (1)" in md and "## Recommended actions" in md

    pdf = client.get(f"/api/v1/runs/{new.id}/export?format=pdf")
    assert pdf.headers["content-type"] == "application/pdf" and pdf.content.startswith(b"%PDF-")
    assert client.get(f"/api/v1/runs/{new.id}/export?format=docx").status_code == 422


def test_diff_against_previous_run(client, db):
    """REQ-001 improved, REQ-002 unchanged, REQ-003 regressed (covered → partial)."""
    _, old, new = _analysis(client, db)
    diff = client.get(f"/api/v1/runs/{new.id}/diff").json()
    assert diff["against_run_id"] == str(old.id)
    changes = {c["code"]: (c["before"], c["after"], c["change"]) for c in diff["changes"]}
    assert changes == {"REQ-001": ("missing", "covered", "improved"),
                       "REQ-002": ("missing", "missing", "unchanged"),
                       "REQ-003": ("covered", "partial", "regressed")}
    assert diff["summary"]["improved"] == 1 and diff["summary"]["regressed"] == 1


def test_diff_with_no_previous_run_and_report_on_incomplete_run(client, db):
    """First run has nothing to compare with; reports need a completed run."""
    _, old, _ = _analysis(client, db)
    assert client.get(f"/api/v1/runs/{old.id}/diff").json()["changes"] == []
    pid = client.post("/api/v1/projects", json={"name": "x"}).json()["id"]
    running = AnalysisRun(project_id=pid, status="running")
    db.add(running)
    db.flush()
    assert client.get(f"/api/v1/runs/{running.id}/report").status_code == 409
