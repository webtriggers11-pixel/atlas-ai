"""
Reports (Phase 11): one structured report per analysis run, rendered as JSON (Report tab),
CSV (traceability matrix), Markdown and PDF — plus a per-requirement diff between two runs.

Everything here is deterministic: it only reorganizes findings that already exist. No LLM calls.
"""
import csv
import io
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AnalysisRun, Finding, Requirement
from app.services.findings_service import get_run_or_404, list_findings

STATUS_ORDER = ["covered", "partial", "unclear", "conflict", "missing"]   # best → worst
STATUS_RANK = {s: i for i, s in enumerate(STATUS_ORDER)}
KIND = {"spec_coverage": "Requirements vs technical documentation", "resume_jd": "Resume vs job description"}


def _evidence_line(e) -> str:
    """'sdd.pdf › 4. Auth › p.7'."""
    return " › ".join(str(x) for x in [e.document_filename, e.section, f"p.{e.page_start}" if e.page_start else None] if x)


def build_report(run_id: UUID, db: Session) -> dict:
    """Structured report for a completed run (the single source for the Report tab and all exports)."""
    run = get_run_or_404(run_id, db)
    if run.status != "completed":
        raise HTTPException(status_code=409, detail="Reports are available for completed runs only.")
    project = run.project
    findings = list_findings(run.id, None, db)
    counts = {s: sum(1 for f in findings if f.status == s) for s in STATUS_ORDER}
    total = len(findings)
    covered_pct = round(100 * counts["covered"] / total) if total else 0
    gaps = counts["missing"] + counts["conflict"] + counts["partial"]

    def items(status):
        """Findings of one status as compact report rows."""
        return [{
            "code": f.requirement.code, "requirement": f.requirement.text, "section": f.requirement.section,
            "assessment": f.explanation, "missing_or_different": f.missing_detail, "action": f.suggested_action,
            "evidence": [{"quote": e.quote, "source": _evidence_line(e), "verified": e.verified} for e in f.evidence],
        } for f in findings if f.status == status]

    if not total:
        headline = "No requirements were analysed."
    elif gaps == 0 and counts["unclear"] == 0:
        headline = f"All {total} requirements are covered by the existing documents."
    else:
        unclear = f" and {counts['unclear']} need a human decision" if counts["unclear"] else ""
        headline = (f"{counts['covered']} of {total} requirements ({covered_pct}%) are fully covered. "
                    f"{counts['missing']} missing, {counts['conflict']} conflicting, {counts['partial']} partial{unclear}.")

    return {
        "analysis": {"id": str(project.id), "name": project.name, "type": KIND.get(project.preset, project.preset)},
        "run": {"id": str(run.id), "finished_at": run.finished_at.isoformat() if run.finished_at else None,
                "model": run.model, "prompt_version": run.prompt_version},
        "documents": [{"name": d.filename, "role": d.role} for d in project.documents if d.status == "indexed"],
        "summary": {"headline": headline, "total": total, "counts": counts, "covered_percent": covered_pct},
        "sections": {
            "missing": items("missing"), "conflict": items("conflict"),
            "partial": items("partial"), "unclear": items("unclear"), "covered": items("covered"),
        },
        "actions": [{"code": f.requirement.code, "status": f.status, "action": f.suggested_action}
                    for f in sorted(findings, key=lambda f: -STATUS_RANK[f.status])
                    if f.suggested_action and f.status != "covered"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


# ── Renderers ───────────────────────────────────────────────────────────────────

def to_csv(report: dict) -> str:
    """Traceability matrix: one row per requirement."""
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["Code", "Requirement", "Section", "Status", "Assessment (AI)", "Missing / different", "Suggested action", "Evidence (verified source text)"])
    for status in STATUS_ORDER[::-1]:
        for row in report["sections"][status]:
            writer.writerow([row["code"], row["requirement"], row["section"] or "", status, row["assessment"],
                             row["missing_or_different"] or "", row["action"] or "",
                             " | ".join(f'{e["source"]}: "{e["quote"]}"' for e in row["evidence"])])
    return out.getvalue()


SECTION_TITLES = [("missing", "Missing areas"), ("conflict", "Conflicts"), ("partial", "Partial areas"),
                  ("unclear", "Needs a human decision"), ("covered", "Covered")]


def to_markdown(report: dict) -> str:
    """Readable report: summary, coverage table, gaps by type, recommended actions, evidence."""
    a, s = report["analysis"], report["summary"]
    lines = [f"# {a['name']}", "", f"*{a['type']}* · generated {report['generated_at'][:16].replace('T', ' ')} UTC", "",
             "## Executive summary", "", s["headline"], "",
             "## Coverage overview", "", "| Status | Requirements |", "|---|---|"]
    lines += [f"| {st.capitalize()} | {s['counts'][st]} |" for st in STATUS_ORDER]
    lines += ["", "Documents: " + ", ".join(f"{d['name']} ({d['role']})" for d in report["documents"]), ""]
    for key, title in SECTION_TITLES:
        rows = report["sections"][key]
        if not rows:
            continue
        lines += [f"## {title} ({len(rows)})", ""]
        for r in rows:
            lines.append(f"### {r['code']} — {r['requirement']}")
            if r["section"]:
                lines.append(f"*Section: {r['section']}*")
            lines += ["", f"**AI assessment:** {r['assessment']}"]
            if r["missing_or_different"]:
                lines.append(f"**Missing / different:** {r['missing_or_different']}")
            for e in r["evidence"]:
                lines.append(f"> \"{e['quote']}\" — {e['source']}{' (verified)' if e['verified'] else ''}")
            lines.append("")
    if report["actions"]:
        lines += ["## Recommended actions", ""]
        lines += [f"- **{x['code']}** ({x['status']}): {x['action']}" for x in report["actions"]]
        lines.append("")
    lines += ["---", f"Run {report['run']['id']} · {report['run']['model']} · {report['run']['prompt_version']}",
              "Quotes are copied from the source documents and verified by code; assessments are AI-generated."]
    return "\n".join(lines)


def _latin1(text: str) -> str:
    """The PDF core fonts are Latin-1 only: map common Unicode punctuation and drop the rest."""
    table = {"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-", "‑": "-",
             "…": "...", "›": ">", "•": "-", " ": " "}
    text = "".join(table.get(ch, ch) for ch in text or "")
    return text.encode("latin-1", errors="replace").decode("latin-1")


def to_pdf(report: dict) -> bytes:
    """Printable PDF version of the Markdown report (fpdf2, core fonts)."""
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_auto_page_break(True, margin=15)
    pdf.add_page()
    line = dict(new_x="LMARGIN", new_y="NEXT")

    def write(text, size=10, style="", h=5.5):
        """One wrapped paragraph."""
        pdf.set_font("Helvetica", style, size)
        pdf.multi_cell(0, h, _latin1(text), **line)

    a, s = report["analysis"], report["summary"]
    write(a["name"], 18, "B", 9)
    write(f"{a['type']} - generated {report['generated_at'][:16].replace('T', ' ')} UTC", 9)
    pdf.ln(3)
    write("Executive summary", 13, "B", 7)
    write(s["headline"])
    pdf.ln(2)
    write("Coverage overview", 13, "B", 7)
    write("   ".join(f"{st.capitalize()}: {s['counts'][st]}" for st in STATUS_ORDER))
    for key, title in SECTION_TITLES:
        rows = report["sections"][key]
        if not rows:
            continue
        pdf.ln(3)
        write(f"{title} ({len(rows)})", 13, "B", 7)
        for r in rows:
            pdf.ln(1)
            write(f"{r['code']} - {r['requirement']}", 10, "B")
            write(f"AI assessment: {r['assessment']}", 9)
            if r["missing_or_different"]:
                write(f"Missing / different: {r['missing_or_different']}", 9)
            for e in r["evidence"]:
                write(f'Source: "{e["quote"]}" - {e["source"]}', 9, "I")
    if report["actions"]:
        pdf.ln(3)
        write("Recommended actions", 13, "B", 7)
        for x in report["actions"]:
            write(f"- {x['code']} ({x['status']}): {x['action']}", 9)
    pdf.ln(4)
    write("Quotes are copied from the source documents and verified by code; assessments are AI-generated.", 8, "I")
    return bytes(pdf.output())


# ── Run diff ────────────────────────────────────────────────────────────────────

def previous_completed_run(run: AnalysisRun, db: Session) -> AnalysisRun | None:
    """The completed run of the same analysis just before `run`."""
    return db.execute(
        select(AnalysisRun).where(AnalysisRun.project_id == run.project_id, AnalysisRun.status == "completed",
                                  AnalysisRun.created_at < run.created_at)
        .order_by(AnalysisRun.created_at.desc()).limit(1)
    ).scalar_one_or_none()


def diff_runs(run_id: UUID, against_id: UUID | None, db: Session) -> dict:
    """Per-requirement status changes between a run and an earlier one (default: the previous completed run)."""
    run = get_run_or_404(run_id, db)
    base = get_run_or_404(against_id, db) if against_id else previous_completed_run(run, db)
    if base is None:
        return {"run_id": str(run.id), "against_run_id": None, "changes": [], "summary": {}}
    if base.project_id != run.project_id:
        raise HTTPException(status_code=422, detail="Both runs must belong to the same analysis.")

    def statuses(r):
        """{requirement_id: (status, code, text)} for one run."""
        rows = db.execute(select(Finding.requirement_id, Finding.status, Requirement.code, Requirement.text)
                          .join(Requirement, Finding.requirement_id == Requirement.id)
                          .where(Finding.run_id == r.id)).all()
        return {rid: (st, code, text) for rid, st, code, text in rows}

    now, before = statuses(run), statuses(base)
    changes = []
    for rid in sorted(set(now) | set(before), key=lambda k: (now.get(k) or before.get(k))[1]):
        new, old = now.get(rid), before.get(rid)
        if new and old:
            kind = ("unchanged" if new[0] == old[0]
                    else "improved" if STATUS_RANK[new[0]] < STATUS_RANK[old[0]]
                    else "regressed")
        else:
            kind = "new" if new else "removed"
        src = new or old
        changes.append({"code": src[1], "requirement": src[2], "before": old[0] if old else None,
                        "after": new[0] if new else None, "change": kind})
    summary = {k: sum(1 for c in changes if c["change"] == k) for k in ("improved", "regressed", "unchanged", "new", "removed")}
    return {"run_id": str(run.id), "against_run_id": str(base.id),
            "against_finished_at": base.finished_at.isoformat() if base.finished_at else None,
            "changes": changes, "summary": summary}
