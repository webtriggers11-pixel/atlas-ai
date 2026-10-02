from fastapi import APIRouter

from app.api.v1 import projects, documents, requirements, runs, settings

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(projects.router)
api_router.include_router(documents.router)
api_router.include_router(requirements.router)
api_router.include_router(runs.router)
api_router.include_router(settings.router)
