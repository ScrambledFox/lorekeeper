from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InternalServerErrorException, NotFoundException
from app.db.database import get_async_session
from app.models.api.claims import ClaimCreate, ClaimResponse
from app.repositories.claims import ClaimRepository
from app.services.claims import ClaimService, get_claim_service

router = APIRouter(prefix="/claims", tags=["claims"])


@router.post(
    "/",
    response_model=list[ClaimResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_claims(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    claim_service: Annotated[ClaimService, Depends(get_claim_service)],
    claims: list[ClaimCreate],
):
    """Create multiple claims."""
    try:
        return await claim_service.create_claims(session, claims)
    except Exception as e:
        raise InternalServerErrorException(message=str(e)) from e


@router.get("", response_model=list[ClaimResponse])
async def list_claims(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    claim_repository: Annotated[ClaimRepository, Depends()],
    skip: int = 0,
    limit: int = 10,
    world_id: str | None = None,
    entity_id: str | None = None,
    canon_state: str | None = None,
    predicate: str | None = None,
) -> list[ClaimResponse]:
    """List claims with pagination."""
    db_claims = await claim_repository.list_claims(
        session,
        skip=skip,
        limit=limit,
        world_id=world_id,
        entity_id=entity_id,
        canon_state=canon_state,
        predicate=predicate,
    )

    return [ClaimResponse.model_validate(db_claim, from_attributes=True) for db_claim in db_claims]


@router.get("/{claim_id}", response_model=ClaimResponse)
async def get_claim(
    claim_id: str,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    claim_repository: Annotated[ClaimRepository, Depends()],
):
    """Get a claim by ID."""
    db_claim = await claim_repository.get_claim(session, claim_id)

    if not db_claim:
        raise NotFoundException(resource="Claim", id=str(claim_id))

    return ClaimResponse.model_validate(db_claim, from_attributes=True)


@router.post("/search", response_model=list[ClaimResponse])
async def search_claims(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    claim_repository: Annotated[ClaimRepository, Depends()],
    query_text: str,
    skip: int = 0,
    limit: int = 10,
) -> list[ClaimResponse]:
    """Search claims by text in predicate or object_value. (semantic search: text → top K claims/chunks with filters)"""
    db_claims = await claim_repository.search_claims(
        session,
        query_text=query_text,
        skip=skip,
        limit=limit,
    )

    return [ClaimResponse.model_validate(db_claim, from_attributes=True) for db_claim in db_claims]
