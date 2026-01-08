"""
Entity API routes for LoreKeeper.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from lorekeeper.api.schemas import EntityCreate, EntityResponse, EntitySearchResult, EntityUpdate
from lorekeeper.db.database import get_async_session
from lorekeeper.db.models import Entity

router = APIRouter(prefix="/worlds/{world_id}/entities", tags=["entities"])


@router.post("", response_model=EntityResponse, status_code=status.HTTP_201_CREATED)
async def create_entity(
    world_id: UUID,
    entity: EntityCreate,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> EntityResponse:
    """Create a new entity in a world."""
    try:
        db_entity = Entity(
            world_id=world_id,
            type=entity.type,
            canonical_name=entity.canonical_name,
            aliases=entity.aliases,
            summary=entity.summary,
            description=entity.description,
            tags=entity.tags,
        )
        session.add(db_entity)
        await session.commit()
        await session.refresh(db_entity)
        return EntityResponse.model_validate(db_entity, from_attributes=True)
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/{entity_id}", response_model=EntityResponse)
async def get_entity(
    world_id: UUID,
    entity_id: UUID,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> EntityResponse:
    """Get an entity by ID."""
    result = await session.execute(
        select(Entity).where(and_(Entity.id == entity_id, Entity.world_id == world_id))
    )
    db_entity = result.scalars().first()

    if not db_entity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entity not found")

    return EntityResponse.model_validate(db_entity, from_attributes=True)


@router.patch("/{entity_id}", response_model=EntityResponse)
async def update_entity(
    world_id: UUID,
    entity_id: UUID,
    update_data: EntityUpdate,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> EntityResponse:
    """Update an entity."""
    result = await session.execute(
        select(Entity).where(and_(Entity.id == entity_id, Entity.world_id == world_id))
    )
    db_entity = result.scalars().first()

    if not db_entity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entity not found")

    # Update only provided fields
    update_dict = update_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(db_entity, key, value)

    try:
        session.add(db_entity)
        await session.commit()
        await session.refresh(db_entity)
        return EntityResponse.model_validate(db_entity, from_attributes=True)
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post("/search", response_model=EntitySearchResult)
async def search_entities(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    world_id: UUID,
    query: str | None = Query(None, description="Search query"),
    entity_type: str | None = Query(None, description="Filter by entity type"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> EntitySearchResult:
    """
    Search entities across multiple fields.

    Searches in:
    - Canonical name
    - Aliases
    - Summary
    - Description
    - Tags
    """
    # Build query
    q = select(Entity).where(Entity.world_id == world_id)

    if query:
        # Search across multiple fields: canonical_name, aliases, summary, description, tags
        search_term = f"%{query}%"
        search_conditions = or_(
            Entity.canonical_name.ilike(search_term),
            Entity.summary.ilike(search_term),
            Entity.description.ilike(search_term),
            # Search for partial matches in aliases array using func.array_to_string
            func.array_to_string(Entity.aliases, " ").ilike(search_term),
            # Also search for partial matches in tags array
            func.array_to_string(Entity.tags, " ").ilike(search_term),
        )
        q = q.where(search_conditions)

    if entity_type:
        q = q.where(Entity.type == entity_type)

    # Get total count
    count_query = select(func.count()).select_from(Entity).where(Entity.world_id == world_id)
    if query:
        search_term = f"%{query}%"
        search_conditions = or_(
            Entity.canonical_name.ilike(search_term),
            Entity.summary.ilike(search_term),
            Entity.description.ilike(search_term),
            # Search for partial matches in aliases array
            func.array_to_string(Entity.aliases, " ").ilike(search_term),
            # Also search for partial matches in tags array
            func.array_to_string(Entity.tags, " ").ilike(search_term),
        )
        count_query = count_query.where(search_conditions)
    if entity_type:
        count_query = count_query.where(Entity.type == entity_type)

    count_result = await session.execute(count_query)
    total = count_result.scalar() or 0

    # Get paginated results
    q = q.offset(offset).limit(limit)
    result = await session.execute(q)
    entities = result.scalars().all()

    return EntitySearchResult(
        total=total,
        results=[EntityResponse.model_validate(e, from_attributes=True) for e in entities],
    )
