from fastapi import APIRouter

from app import llm
from app.core.config import settings
from app.schemas.project import ProviderInfo, SettingsResponse

router = APIRouter(prefix="/settings", tags=["settings"])

APP_VERSION = "2.0.0-dev"


# GET /api/v1/settings
# Example response: {"version": "2.0.0-dev", "default_provider": "groq",
#                    "providers": [{"name": "groq", "configured": true, "model": "openai/gpt-oss-20b"}, ...],
#                    "retrieval_mode": "vector", "max_upload_mb": 20, "background_jobs": "worker", ...}
@router.get("", response_model=SettingsResponse)
def get_settings():
    """Read-only server configuration for the Settings page — provider keys are never returned."""
    models = {"groq": settings.GROQ_MODEL, "gemini": settings.GEMINI_MODEL, "ollama": settings.OLLAMA_MODEL}
    return SettingsResponse(
        version=APP_VERSION,
        default_provider=settings.LLM_PROVIDER,
        providers=[ProviderInfo(name=n, configured=llm._is_configured(n), model=m) for n, m in models.items()],
        embedding_model=settings.EMBEDDING_MODEL,
        retrieval_mode=settings.RETRIEVAL_MODE,
        prompt_versions=dict(llm.PROMPT_VERSIONS),
        max_upload_mb=settings.MAX_UPLOAD_MB,
        max_pdf_pages=settings.MAX_PDF_PAGES,
        background_jobs="inline" if settings.CELERY_TASK_ALWAYS_EAGER else "worker",
    )
