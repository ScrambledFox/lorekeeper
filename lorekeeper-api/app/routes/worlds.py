"""
World API routes for LoreKeeper.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InternalServerErrorException, NotFoundException
from app.db.database import get_async_session
from app.models.api.worlds import WorldCreate, WorldResponse
from app.models.db.worlds import World

router = APIRouter(prefix="/worlds", tags=["worlds"])


@router.post("", response_model=WorldResponse, status_code=status.HTTP_201_CREATED)
async def create_world(
    world: WorldCreate,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> WorldResponse:
    """Create a new world."""
    try:
        db_world = World(
            name=world.name,
            description=world.description,
            meta=world.meta.model_dump() if world.meta else None,
        )

        session.add(db_world)
        await session.commit()
        await session.refresh(db_world)
        return WorldResponse.model_validate(db_world, from_attributes=True)
    except Exception as e:
        await session.rollback()
        raise InternalServerErrorException(message=str(e)) from e


@router.get("/{world_id}", response_model=WorldResponse)
async def get_world(
    world_id: UUID,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> WorldResponse:
    """Get a world by ID."""
    result = await session.execute(select(World).where(World.id == world_id))
    db_world = result.scalars().first()

    if not db_world:
        raise NotFoundException(resource="World", id=str(world_id))

    return WorldResponse.model_validate(db_world, from_attributes=True)


@router.get("/", response_model=list[WorldResponse])
async def list_worlds(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    skip: int = 0,
    limit: int = 10,
) -> list[WorldResponse]:
    """List worlds with pagination."""
    result = await session.execute(select(World).offset(skip).limit(limit))
    db_worlds = result.scalars().all()

    return [WorldResponse.model_validate(db_world, from_attributes=True) for db_world in db_worlds]
