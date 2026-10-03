"""Request/response models for the V2 /api/v1 endpoints (projects, documents, requirements, runs, findings)."""
from uuid import UUID
from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator

Preset = Literal["spec_coverage", "resume_jd"]
DocumentRole = Literal["reference", "existing"]
DocumentStatus = Literal["uploaded", "processing", "indexed", "failed"]
RequirementStatus = Literal["draft", "approved", "rejected"]
RunStatus = Literal["queued", "running", "completed", "failed"]
FindingStatus = Literal["covered", "partial", "missing", "conflict", "unclear"]


def _strip_non_empty(value: str) -> str:
    """Trim whitespace and reject strings that are empty afterwards."""
    value = value.strip()
    if not value:
        raise ValueError("must not be blank")
    return value


# ── Projects ──────────────────────────────────────────────────────────────────

class ProjectCreate(BaseModel):
    name: str = Field(max_length=200)
    preset: Preset = "spec_coverage"

    _clean_name = field_validator("name")(_strip_non_empty)


class ProjectUpdate(BaseModel):
    name: str = Field(max_length=200)

    _clean_name = field_validator("name")(_strip_non_empty)


class ProjectResponse(BaseModel):
    id: UUID
    name: str
    preset: Preset
    created_at: datetime
    updated_at: datetime
    reference_documents: int = 0
    existing_documents: int = 0
    requirements: int = 0
    approved_requirements: int = 0
    latest_run_status: Optional[RunStatus] = None
    extraction_status: Literal["idle", "running", "completed", "failed"] = "idle"
    extraction_error: Optional[str] = None
    extracted_at: Optional[datetime] = None
    finding_counts: Optional[dict[str, int]] = None   # from the latest COMPLETED run
    last_analyzed_at: Optional[datetime] = None


# ── Documents ─────────────────────────────────────────────────────────────────

class DocumentResponse(BaseModel):
    id: UUID
    project_id: UUID
    role: DocumentRole
    filename: str
    file_type: str
    size_bytes: int
    status: DocumentStatus
    error_message: Optional[str] = None
    page_count: Optional[int] = None
    chunk_count: int
    created_at: datetime
    processed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ChunkResponse(BaseModel):
    id: UUID
    document_id: UUID
    chunk_index: int
    content: str
    section: Optional[str] = None
    page_start: Optional[int] = None
    page_end: Optional[int] = None

    model_config = {"from_attributes": True}


# ── Requirements ──────────────────────────────────────────────────────────────

class RequirementCreate(BaseModel):
    text: str = Field(max_length=4000)
    section: Optional[str] = Field(default=None, max_length=300)

    _clean_text = field_validator("text")(_strip_non_empty)


class RequirementUpdate(BaseModel):
    text: Optional[str] = Field(default=None, max_length=4000)
    section: Optional[str] = Field(default=None, max_length=300)
    status: Optional[RequirementStatus] = None

    @field_validator("text")
    @classmethod
    def _clean_text(cls, value: Optional[str]) -> Optional[str]:
        """Trim text when provided; reject blank text."""
        return None if value is None else _strip_non_empty(value)


class RequirementMerge(BaseModel):
    ids: list[UUID] = Field(min_length=2)
    text: Optional[str] = Field(default=None, max_length=4000)


class ApproveAllResponse(BaseModel):
    approved: int


class RequirementResponse(BaseModel):
    id: UUID
    project_id: UUID
    code: str
    text: str
    section: Optional[str] = None
    status: RequirementStatus
    origin: Literal["extracted", "manual"]
    source_chunk_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Runs & findings ───────────────────────────────────────────────────────────

class RunResponse(BaseModel):
    id: UUID
    project_id: UUID
    status: RunStatus
    total: int
    processed: int
    model: Optional[str] = None
    prompt_version: Optional[str] = None
    stats: Optional[dict] = None
    error_message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class EvidenceResponse(BaseModel):
    id: UUID
    chunk_id: UUID
    document_id: UUID
    document_filename: str
    document_role: DocumentRole
    section: Optional[str] = None
    page_start: Optional[int] = None
    quote: str
    verified: bool
    score: Optional[float] = None


class RequirementRef(BaseModel):
    id: UUID
    code: str
    text: str
    section: Optional[str] = None
    source_document: Optional[str] = None   # reference document the requirement was extracted from
    source_page: Optional[int] = None


class FindingResponse(BaseModel):
    id: UUID
    run_id: UUID
    requirement: RequirementRef
    status: FindingStatus
    confidence: Optional[float] = None
    explanation: str
    missing_detail: Optional[str] = None
    suggested_action: Optional[str] = None
    source: Literal["pipeline", "agent", "cache"]
    evidence: list[EvidenceResponse]
    created_at: datetime
    updated_at: datetime


# ── Search ────────────────────────────────────────────────────────────────────

class SearchRequest(BaseModel):
    query: str = Field(max_length=2000)
    role: Optional[DocumentRole] = None
    k: int = Field(default=5, ge=1, le=50)
    mode: Optional[Literal["vector", "hybrid"]] = None   # None = server default (RETRIEVAL_MODE)

    _clean_query = field_validator("query")(_strip_non_empty)


class SearchResult(BaseModel):
    chunk_id: UUID
    document_id: UUID
    document_filename: str
    document_role: DocumentRole
    section: Optional[str] = None
    page_start: Optional[int] = None
    content: str
    score: float
    rank: int


class DocumentListItem(DocumentResponse):
    """A document plus the analysis (project) it belongs to — for the global Documents page."""
    project_name: str


class ProviderInfo(BaseModel):
    name: str
    configured: bool
    model: str


class SettingsResponse(BaseModel):
    """Read-only server configuration for the Settings page. Never contains secrets."""
    version: str
    default_provider: str
    providers: list[ProviderInfo]
    embedding_model: str
    retrieval_mode: str
    prompt_versions: dict[str, str]
    max_upload_mb: int
    max_pdf_pages: int
    background_jobs: Literal["worker", "inline"]


# ── Ask your analysis (tool calling) ──────────────────────────────────────────

class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=8000)


class ChatRequest(BaseModel):
    message: str = Field(max_length=2000)
    history: list[ChatTurn] = Field(default_factory=list, max_length=20)

    _clean_message = field_validator("message")(_strip_non_empty)


class ChatStep(BaseModel):
    tool: str
    arguments: dict
    ok: bool
    summary: str


class ChatSource(BaseModel):
    kind: Literal["chunk", "requirement"]
    id: str
    document_id: Optional[str] = None
    document: Optional[str] = None
    section: Optional[str] = None
    page: Optional[int] = None
    status: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    steps: list[ChatStep]
    sources: list[ChatSource]
    stopped_by_budget: bool
    duration_s: float
    model: str
