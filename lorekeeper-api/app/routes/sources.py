from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InternalServerErrorException
from app.db.database import get_async_session
from app.models.api.sources import (
    SourceChunkCreate,
    SourceChunkResponse,
    SourceCreate,
    SourceResponse,
)
from app.services.sources import SourceService, get_source_service

router = APIRouter(prefix="/sources", tags=["sources"])


@router.post("/")
async def create_source(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    source_service: Annotated[SourceService, Depends(get_source_service)],
    source: SourceCreate,
):
    """Create a new source."""
    try:
        return await source_service.create_source(session, source)
    except Exception as e:
        raise InternalServerErrorException(message=str(e)) from e


@router.post(
    "/{source_id}/chunks/",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=list[SourceChunkResponse],
)
async def create_source_chunk(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    source_service: Annotated[SourceService, Depends(get_source_service)],
    source_id: str,
    chunks: list[SourceChunkCreate],
):
    """Create a new source chunk."""
    try:
        return await source_service.create_source_chunks(session, source_id, chunks)
    except Exception as e:
        raise InternalServerErrorException(message=str(e)) from e


@router.get("/{source_id}", response_model=SourceResponse)
async def get_source(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    source_service: Annotated[SourceService, Depends(get_source_service)],
    source_id: str,
):
    """Retrieve a source by its ID."""
    try:
        return await source_service.get_source(session, source_id)
    except Exception as e:
        raise InternalServerErrorException(message=str(e)) from e
