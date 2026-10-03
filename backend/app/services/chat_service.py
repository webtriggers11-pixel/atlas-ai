"""
"Ask your analysis" — question answering over one analysis with tool calling.

The model gets READ-ONLY tools. Every tool is built for one analysis (project_id is bound
here, on the server), so the model can't choose which analysis it reads — it physically
cannot reach another project's data. Tool arguments are validated with Pydantic.
"""
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app import llm
from app.models import AnalysisRun, DocChunk, Finding, ProjectDocument, Requirement, Evidence
from app.services import retrieval
from app.services.project_service import get_project_or_404
from app.services.tool_loop import Tool, run_tool_loop

MAX_TOOL_CALLS = 6
TEXT_LIMIT = 700   # characters of chunk text returned per search hit


# ── Tool argument models (become the JSON schema the model sees) ───────────────

class SearchArgs(BaseModel):
    query: str = Field(min_length=2, max_length=300, description="What to look for, in plain words")
    role: Optional[Literal["reference", "existing"]] = Field(
        default=None, description="'reference' = what should exist, 'existing' = current state; omit for both")
    k: int = Field(default=5, ge=1, le=8, description="How many passages to return")


class ListFindingsArgs(BaseModel):
    status: Optional[Literal["covered", "partial", "missing", "conflict", "unclear"]] = Field(
        default=None, description="Only findings with this status")
    keyword: Optional[str] = Field(default=None, max_length=100, description="Only requirements containing this word")


class RequirementArgs(BaseModel):
    code: str = Field(min_length=3, max_length=20, description="Requirement code, e.g. REQ-004")


class ChunkArgs(BaseModel):
    chunk_id: str = Field(description="chunk_id returned by search_documents or get_requirement")


class NoArgs(BaseModel):
    pass


# ── Tool implementations (project_id bound by build_tools) ─────────────────────

def _latest_completed_run(project_id: UUID, db: Session) -> AnalysisRun | None:
    """Most recent completed analysis run for the project."""
    return db.execute(
        select(AnalysisRun).where(AnalysisRun.project_id == project_id, AnalysisRun.status == "completed")
        .order_by(AnalysisRun.created_at.desc()).limit(1)
    ).scalar_one_or_none()


def build_tools(project_id: UUID, db: Session) -> list[Tool]:
    """The read-only tool set for one analysis. project_id is captured here, never taken from the model."""

    def search_documents(args: SearchArgs):
        """Semantic search over the analysis's documents."""
        hits = retrieval.search(project_id, args.query, db, role=args.role, k=args.k)
        return {"results": [{
            "chunk_id": str(h.chunk.id), "document_id": str(h.document.id), "document": h.document.filename, "role": h.document.role,
            "section": h.chunk.section, "page": h.chunk.page_start, "similarity": round(h.score, 3),
            "text": h.chunk.content[:TEXT_LIMIT],
        } for h in hits]}

    def list_findings(args: ListFindingsArgs):
        """Findings of the latest completed run, optionally filtered."""
        run = _latest_completed_run(project_id, db)
        if run is None:
            return {"error": "this analysis has not been run yet"}
        query = select(Finding).join(Finding.requirement).where(Finding.run_id == run.id).options(selectinload(Finding.requirement))
        if args.status:
            query = query.where(Finding.status == args.status)
        if args.keyword:
            query = query.where(Requirement.text.ilike(f"%{args.keyword}%"))
        findings = db.execute(query.order_by(Requirement.code)).scalars().all()
        return {"counts": (run.stats or {}).get("counts"), "results": [{
            "code": f.requirement.code, "status": f.status, "requirement": f.requirement.text,
            "section": f.requirement.section, "assessment": f.explanation[:240],
        } for f in findings]}

    def get_requirement(args: RequirementArgs):
        """One requirement with its finding and verified evidence quotes."""
        req = db.execute(select(Requirement).where(
            Requirement.project_id == project_id, Requirement.code == args.code.strip().upper())).scalar_one_or_none()
        if req is None:
            return {"error": f"no requirement {args.code} in this analysis"}
        out = {"code": req.code, "text": req.text, "section": req.section, "review_status": req.status}
        run = _latest_completed_run(project_id, db)
        finding = run and db.execute(
            select(Finding).where(Finding.run_id == run.id, Finding.requirement_id == req.id)
            .options(selectinload(Finding.evidence).selectinload(Evidence.chunk).selectinload(DocChunk.document))
        ).scalar_one_or_none()
        if finding:
            out["finding"] = {
                "status": finding.status, "confidence": finding.confidence, "assessment": finding.explanation,
                "missing_or_different": finding.missing_detail, "suggested_action": finding.suggested_action,
                "evidence": [{"quote": e.quote, "chunk_id": str(e.chunk_id), "document": e.chunk.document.filename,
                              "section": e.chunk.section, "page": e.chunk.page_start} for e in finding.evidence],
            }
        return out

    def get_chunk(args: ChunkArgs):
        """Full text of one chunk plus its neighbours — only if it belongs to this analysis."""
        try:
            chunk_id = UUID(args.chunk_id)
        except ValueError:
            return {"error": "chunk_id is not a valid id"}
        chunk = db.execute(
            select(DocChunk).join(ProjectDocument, DocChunk.document_id == ProjectDocument.id)
            .where(DocChunk.id == chunk_id, ProjectDocument.project_id == project_id)
        ).scalar_one_or_none()
        if chunk is None:
            return {"error": "chunk not found in this analysis"}
        neighbours = db.execute(select(DocChunk).where(
            DocChunk.document_id == chunk.document_id,
            DocChunk.chunk_index.in_([chunk.chunk_index - 1, chunk.chunk_index + 1]),
        ).order_by(DocChunk.chunk_index)).scalars().all()
        return {
            "chunk_id": str(chunk.id), "document_id": str(chunk.document_id), "document": chunk.document.filename, "section": chunk.section,
            "page": chunk.page_start, "text": chunk.content,
            "neighbours": [{"chunk_id": str(n.id), "section": n.section, "text": n.content[:TEXT_LIMIT]} for n in neighbours],
        }

    def get_overview(_: NoArgs):
        """Analysis summary: documents, requirement counts, latest results."""
        project = get_project_or_404(project_id, db)
        docs = db.execute(select(ProjectDocument).where(ProjectDocument.project_id == project_id)).scalars().all()
        run = _latest_completed_run(project_id, db)
        return {
            "analysis": project.name, "type": project.preset,
            "documents": [{"name": d.filename, "role": d.role, "status": d.status, "chunks": d.chunk_count} for d in docs],
            "requirements": {"total": len(project.requirements),
                             "approved": sum(1 for r in project.requirements if r.status == "approved")},
            "latest_results": (run.stats or {}).get("counts") if run else None,
        }

    return [
        Tool("get_overview", "Summary of this analysis: documents, requirement counts and the latest result counts.", NoArgs, get_overview),
        Tool("list_findings", "List findings (requirement + status + short assessment) from the latest analysis run.", ListFindingsArgs, list_findings),
        Tool("get_requirement", "Full details for one requirement code: its finding, assessment and verified evidence quotes.", RequirementArgs, get_requirement),
        Tool("search_documents", "Semantic search over the documents. Returns passages with chunk_id, document, section and page.", SearchArgs, search_documents),
        Tool("get_chunk", "Read the full text of a passage (and its neighbours) by chunk_id.", ChunkArgs, get_chunk),
    ]


# ── Ask ─────────────────────────────────────────────────────────────────────────

def _sources(steps) -> list[dict]:
    """Passages and requirements the tools returned — shown to the user as 'sources used'."""
    sources, seen = [], set()
    for step in steps:
        data = step.data if isinstance(step.data, dict) else {}
        for r in data.get("results", []):
            if "chunk_id" in r and r["chunk_id"] not in seen:
                seen.add(r["chunk_id"])
                sources.append({"kind": "chunk", "id": r["chunk_id"], "document_id": r.get("document_id"),
                                "document": r["document"], "section": r.get("section"), "page": r.get("page")})
            elif "code" in r and r["code"] not in seen:
                seen.add(r["code"])
                sources.append({"kind": "requirement", "id": r["code"], "status": r.get("status")})
        if "code" in data and data["code"] not in seen:
            seen.add(data["code"])
            sources.append({"kind": "requirement", "id": data["code"], "status": (data.get("finding") or {}).get("status")})
        if step.tool == "get_chunk" and "chunk_id" in data and data["chunk_id"] not in seen:
            seen.add(data["chunk_id"])
            sources.append({"kind": "chunk", "id": data["chunk_id"], "document_id": data.get("document_id"),
                            "document": data["document"], "section": data.get("section"), "page": data.get("page")})
    return sources


def ask(project_id: UUID, question: str, history: list[dict], db: Session) -> dict:
    """Answer a question about one analysis using the read-only tools."""
    project = get_project_or_404(project_id, db)
    kind = "resume vs job description" if project.preset == "resume_jd" else "requirements vs technical documentation"
    messages = [{"role": "system", "content": llm.chat_system_prompt(project.name, kind)}]
    messages += [{"role": m["role"], "content": m["content"]} for m in history[-8:]]
    messages.append({"role": "user", "content": question})

    with llm.call_context(f"chat:{project_id}"):
        result = run_tool_loop(messages, build_tools(project_id, db), task_type="chat", max_tool_calls=MAX_TOOL_CALLS)

    return {
        "answer": result.answer or "I couldn't produce an answer — please rephrase the question.",
        "steps": [{"tool": s.tool, "arguments": s.arguments, "ok": s.ok, "summary": s.summary} for s in result.steps],
        "sources": _sources(result.steps),
        "stopped_by_budget": result.stopped_by_budget,
        "duration_s": result.duration_s,
        "model": llm.model_label("chat"),
    }
