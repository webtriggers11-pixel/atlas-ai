"""
End-to-end smoke run on any two real files — the full product flow, no labels needed.

    upload reference + existing → process (extract, chunk, embed) → AI requirement
    extraction → approve all → gap analysis → print findings with evidence

Usage (from backend/):
    python -m eval.smoke_run --reference path/to/job_description.md --existing path/to/resume.pdf --preset resume_jd
    python -m eval.smoke_run --reference srs.docx --existing sdd.pdf --keep      # keep the project afterwards

Runs against the TEST database (same safety rule as the tests) and deletes the
project afterwards unless --keep is given. Files are read from disk only; nothing
is copied into the repository.
"""
import argparse
import sys
import time
from pathlib import Path

from eval.run_eval import DATABASE_NAME  # noqa: F401 — importing configures env for the test DB first

from app.core.config import settings  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models import Finding, Requirement  # noqa: E402
from app.schemas.project import ProjectCreate  # noqa: E402
from app.services import analysis_service, extraction_job, findings_service, ingestion_service, project_service  # noqa: E402
from sqlalchemy import select  # noqa: E402


def main():
    """Run the whole flow on two files and print a readable report."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--reference", required=True, type=Path)
    parser.add_argument("--existing", required=True, type=Path)
    parser.add_argument("--preset", default="spec_coverage", choices=["spec_coverage", "resume_jd"])
    parser.add_argument("--keep", action="store_true", help="keep the project in the test database")
    args = parser.parse_args()

    db = SessionLocal()
    started = time.perf_counter()
    project = project_service.create_project(ProjectCreate(name=f"smoke: {args.existing.name}", preset=args.preset), db)
    try:
        for role, path in (("reference", args.reference), ("existing", args.existing)):
            doc, _ = ingestion_service.upload_document(project.id, role, path.name, path.read_bytes(), db)
            db.refresh(doc)
            print(f"[{role}] {path.name}: {doc.status}, {doc.chunk_count} chunks, {doc.page_count or '-'} pages"
                  + (f" — {doc.error_message}" if doc.error_message else ""))
            if doc.status != "indexed":
                return

        extraction_job.start_extraction(project.id, db)
        db.expire_all()
        reqs = db.execute(select(Requirement).where(Requirement.project_id == project.id).order_by(Requirement.code)).scalars().all()
        p = project_service.get_project(project.id, db)
        print(f"\nExtraction: {p.extraction_status}, {len(reqs)} requirements" + (f" — {p.extraction_error}" if p.extraction_error else ""))
        for r in reqs:
            print(f"  {r.code} [{r.section or '-'}] {r.text}")
        if not reqs:
            return

        from app.services.requirement_service import approve_all
        approve_all(project.id, db)
        run = analysis_service.start_analysis(project.id, db)
        db.refresh(run)
        print(f"\nAnalysis: {run.status} ({run.model}, {run.prompt_version})" + (f" — {run.error_message}" if run.error_message else ""))
        print(f"Stats: {run.stats}")

        print("\nFindings:")
        for f in findings_service.list_findings(run.id, None, db):
            print(f"\n  {f.requirement.code} {f.status.upper():9s} conf={f.confidence}  {f.requirement.text}")
            print(f"     why: {f.explanation}")
            if f.missing_detail:
                print(f"     missing: {f.missing_detail}")
            for e in f.evidence:
                where = f"{e.document_filename}" + (f" p.{e.page_start}" if e.page_start else "") + (f" [{e.section}]" if e.section else "")
                print(f"     evidence ({where}, verified={e.verified}): \"{e.quote}\"")
        print(f"\nTotal time {time.perf_counter() - started:.0f}s, retrieval={settings.RETRIEVAL_MODE}")
    finally:
        if not args.keep:
            db.rollback()
            project_service.delete_project(project.id, db)
        db.close()


if __name__ == "__main__":
    main()
