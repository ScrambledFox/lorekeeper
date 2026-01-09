"""
API routes for claim management.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from lorekeeper.api.schemas import ClaimCreate, ClaimResponse, ClaimUpdate
from lorekeeper.api.services.contradiction_detector import check_claim_contradictions
from lorekeeper.db.database import get_async_session
from lorekeeper.db.models import Claim, World

router = APIRouter(prefix="/worlds/{world_id}/claims", tags=["claims"])


@router.post("", response_model=ClaimResponse, status_code=status.HTTP_201_CREATED)
async def create_claim(
    world_id: UUID,
    claim_create: ClaimCreate,
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """
    Create a new claim.

    During creation:
    - If claim is CANON_TRUE (factual), validate it doesn't contradict existing canon.
      If it does, reject the claim with a 409 Conflict error.
    - If claim is CANON_FALSE (a lie/myth), check it isn't actually true.
      If it is, reject with a 409 Conflict error.
    """
    # Check if world exists
    world_query = select(World).where(World.id == world_id)
    world_result = await session.execute(world_query)
    world = world_result.scalar_one_or_none()
    if not world:
        raise HTTPException(status_code=404, detail="World not found")

    # Perform contradiction check during ingestion
    contradiction_error = await check_claim_contradictions(claim_create, world_id, session)
    if contradiction_error:
        raise HTTPException(status_code=409, detail=contradiction_error)

    db_claim = Claim(world_id=world_id, **claim_create.model_dump())
    session.add(db_claim)
    await session.commit()
    await session.refresh(db_claim)
    return db_claim


@router.get("/{claim_id}", response_model=ClaimResponse)
async def get_claim(
    world_id: UUID,
    claim_id: UUID,
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Retrieve a specific claim."""
    query = select(Claim).where(and_(Claim.id == claim_id, Claim.world_id == world_id))
    result = await session.execute(query)
    claim = result.scalar_one_or_none()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    return claim


@router.patch("/{claim_id}", response_model=ClaimResponse)
async def update_claim(
    world_id: UUID,
    claim_id: UUID,
    claim_update: ClaimUpdate,
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Update a claim's truth status or notes."""
    query = select(Claim).where(and_(Claim.id == claim_id, Claim.world_id == world_id))
    result = await session.execute(query)
    claim = result.scalar_one_or_none()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    for key, value in claim_update.model_dump(exclude_unset=True).items():
        setattr(claim, key, value)

    await session.commit()
    await session.refresh(claim)
    return claim


@router.delete("/{claim_id}")
async def delete_claim(
    world_id: UUID,
    claim_id: UUID,
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Delete a claim."""
    query = select(Claim).where(and_(Claim.id == claim_id, Claim.world_id == world_id))
    result = await session.execute(query)
    claim = result.scalar_one_or_none()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    await session.delete(claim)
    await session.commit()
    return {"message": "Claim deleted"}


@router.get("", response_model=list[ClaimResponse])
async def list_claims(
    world_id: UUID,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    entity_id: UUID | None = Query(None),
    truth_status: str | None = Query(None),
    predicate: str | None = Query(None),
    skip: int = Query(0),
    limit: int = Query(100),
) -> list[ClaimResponse]:
    """List claims with optional filters."""
    query = select(Claim).where(Claim.world_id == world_id)

    if entity_id:
        query = query.where(Claim.subject_entity_id == entity_id)
    if truth_status:
        query = query.where(Claim.truth_status == truth_status)
    if predicate:
        query = query.where(Claim.predicate == predicate)

    query = query.offset(skip).limit(limit)
    result = await session.execute(query)
    claims = result.scalars().all()
    return list(claims)
