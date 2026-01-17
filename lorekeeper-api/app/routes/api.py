from fastapi import APIRouter

from app.core.config import settings
from app.models.api.api import ApiHealthResponse, ApiInfoResponse, ApiStatusResponse

router = APIRouter()


@router.get("/")
async def root() -> ApiStatusResponse:
    """Health check endpoint."""
    return ApiStatusResponse(
        status="ok",
        service="LoreKeeper API",
        version=settings.API_VERSION,
    )


@router.get("/info")
async def info() -> ApiInfoResponse:
    """API information endpoint."""
    return ApiInfoResponse(
        name=settings.API_TITLE,
        version=settings.API_VERSION,
        description=settings.API_DESCRIPTION,
        environment=settings.ENVIRONMENT,
    )


@router.get("/health")
async def health() -> ApiHealthResponse:
    """Health check endpoint."""
    return ApiHealthResponse(status="healthy")
