from fastapi import APIRouter, Depends

from app.api.v1 import auth, projects, documents, requirements, runs, settings
from app.core.security import authenticate

# Everything except /auth requires a valid token when AUTH_ENABLED=true (no-op otherwise)
protected = APIRouter(dependencies=[Depends(authenticate)])
protected.include_router(projects.router)
protected.include_router(documents.router)
protected.include_router(requirements.router)
protected.include_router(runs.router)
protected.include_router(settings.router)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(protected)
