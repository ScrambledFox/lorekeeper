from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InternalServerErrorException, NotFoundException
from app.db.database import get_async_session
from app.models.api.entities import (
    EntityAliasCreate,
    EntityAliasResponse,
    EntityCreate,
    EntityResponse,
)
from app.models.db.entities import Entity, EntityAlias

router = APIRouter(prefix="/entities", tags=["entities"])


@router.post("/", response_model=EntityResponse, status_code=status.HTTP_201_CREATED)
async def create_entity(
    entity: EntityCreate,
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Create a new entity."""
    try:
        db_entity = Entity(
            world_id=entity.world_id,
            type=entity.type,
            name=entity.name,
            summary=entity.summary,
            description=entity.description,
            meta=entity.meta,
        )

        session.add(db_entity)
        await session.commit()
        await session.refresh(db_entity)
        return EntityResponse.model_validate(db_entity, from_attributes=True)
    except Exception as e:
        await session.rollback()
        raise InternalServerErrorException(message=str(e)) from e


@router.get("/{entity_id}", response_model=EntityResponse)
async def get_entity(
    entity_id: str,
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Get an entity by ID."""
    result = await session.execute(select(Entity).where(Entity.id == entity_id))
    db_entity = result.scalars().first()

    if not db_entity:
        raise NotFoundException(resource="Entity", id=str(entity_id))

    return EntityResponse.model_validate(db_entity, from_attributes=True)


@router.get("/", response_model=list[EntityResponse])
async def list_entities(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    skip: int = 0,
    limit: int = 10,
    world_id: str | None = None,
    type: str | None = None,
    q: str | None = None,
) -> list[EntityResponse]:
    """List entities with pagination."""
    query = select(Entity)

    if world_id:
        query = query.where(Entity.world_id == world_id)
    if type:
        query = query.where(Entity.type == type)
    if q:
        search = f"%{q}%"
        query = query.where(
            Entity.name.ilike(search)
            | Entity.summary.ilike(search)
            | Entity.description.ilike(search)
        )

    query = query.offset(skip).limit(limit)

    result = await session.execute(query)
    db_entities = result.scalars().all()

    return [
        EntityResponse.model_validate(db_entity, from_attributes=True) for db_entity in db_entities
    ]


@router.post(
    "/{entity_id}/aliases", response_model=EntityAliasResponse, status_code=status.HTTP_201_CREATED
)
async def create_entity_alias(
    session: Annotated[AsyncSession, Depends(get_async_session)], alias: EntityAliasCreate
):
    """Create a new alias for an entity."""
    try:
        db_alias = EntityAlias(
            entity_id=alias.entity_id,
            alias=alias.alias,
            locale=alias.locale,
            source_note=alias.source_note,
        )

        session.add(db_alias)
        await session.commit()
        await session.refresh(db_alias)
        return EntityAliasResponse.model_validate(db_alias, from_attributes=True)
    except Exception as e:
        await session.rollback()
        raise InternalServerErrorException(message=str(e)) from e
