"""
World API routes for LoreKeeper.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lorekeeper.api.schemas import WorldCreate, WorldResponse
from lorekeeper.db.database import get_async_session
from lorekeeper.db.models import World

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
        )
        session.add(db_world)
        await session.commit()
        await session.refresh(db_world)
        return WorldResponse.from_orm(db_world)
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{world_id}", response_model=WorldResponse)
async def get_world(
    world_id: UUID,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> WorldResponse:
    """Get a world by ID."""
    result = await session.execute(select(World).where(World.id == world_id))
    db_world = result.scalars().first()

    if not db_world:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="World not found")

    return WorldResponse.from_orm(db_world)
