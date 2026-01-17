"""Validation utilities for asset operations."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, NotFoundException, UnauthorizedException
from app.models.db.claims import Claim
from app.models.db.entities import Entity
from app.models.db.sources import Source, SourceChunk
from app.models.db.worlds import World


class AssetValidationError(Exception):
    """Base exception for asset validation errors."""

    pass


class WorldNotFoundError(AssetValidationError):
    """Raised when a world is not found."""

    pass


class ReferenceNotFoundError(AssetValidationError):
    """Raised when a referenced lore entity is not found."""

    pass


class WorldScopeViolationError(AssetValidationError):
    """Raised when a referenced entity doesn't belong to the specified world."""

    pass


async def validate_world_exists(world_id: UUID, session: AsyncSession) -> None:
    """Validate that a world exists."""
    result = await session.execute(select(World).where(World.id == world_id))
    if not result.scalars().first():
        raise WorldNotFoundError(f"World {world_id} not found")


async def validate_world_scoping(
    world_id: UUID,
    claim_ids: list[UUID],
    entity_ids: list[UUID],
    source_chunk_ids: list[UUID],
    source_id: UUID | None,
    session: AsyncSession,
) -> None:
    """Validate that all referenced entities belong to the specified world."""
    # Check all claims belong to world
    if claim_ids:
        result = await session.execute(
            select(Claim).where(Claim.id.in_(claim_ids) & (Claim.world_id != world_id))
        )
        if result.scalars().first():
            raise WorldScopeViolationError(
                "One or more claims do not belong to the specified world"
            )

    # Check all entities belong to world
    if entity_ids:
        result = await session.execute(
            select(Entity).where(Entity.id.in_(entity_ids) & (Entity.world_id != world_id))
        )
        if result.scalars().first():
            raise WorldScopeViolationError(
                "One or more entities do not belong to the specified world"
            )

    # Check all source chunks belong to world (via source)
    if source_chunk_ids:
        result = await session.execute(
            select(SourceChunk).where(SourceChunk.id.in_(source_chunk_ids))
        )
        chunks = result.scalars().all()
        if len(chunks) != len(source_chunk_ids):
            raise ReferenceNotFoundError("One or more source chunks not found")

        # Get sources for these chunks
        source_ids = {chunk.source_id for chunk in chunks}
        result = await session.execute(select(Source).where(Source.id.in_(source_ids)))
        sources = result.scalars().all()
        for source in sources:
            if source.world_id != world_id:
                raise WorldScopeViolationError(
                    "One or more source chunks do not belong to the specified world"
                )

    # Check source belongs to world
    if source_id:
        result = await session.execute(select(Source).where(Source.id == source_id))
        source = result.scalars().first()
        if not source:
            raise ReferenceNotFoundError(f"Source {source_id} not found")
        if source.world_id != world_id:
            raise WorldScopeViolationError(
                f"Source {source_id} does not belong to world {world_id}"
            )


async def validate_references_exist(
    claim_ids: list[UUID],
    entity_ids: list[UUID],
    source_chunk_ids: list[UUID],
    session: AsyncSession,
) -> None:
    """Validate that all referenced entities exist."""
    # Check claims exist
    if claim_ids:
        result = await session.execute(select(Claim).where(Claim.id.in_(claim_ids)))
        found_claims = {claim.id for claim in result.scalars().all()}
        if len(found_claims) != len(claim_ids):
            missing = set(claim_ids) - found_claims
            raise ReferenceNotFoundError(f"Claims not found: {missing}")

    # Check entities exist
    if entity_ids:
        result = await session.execute(select(Entity).where(Entity.id.in_(entity_ids)))
        found_entities = {entity.id for entity in result.scalars().all()}
        if len(found_entities) != len(entity_ids):
            missing = set(entity_ids) - found_entities
            raise ReferenceNotFoundError(f"Entities not found: {missing}")

    # Check source chunks exist
    if source_chunk_ids:
        result = await session.execute(
            select(SourceChunk).where(SourceChunk.id.in_(source_chunk_ids))
        )
        found_chunks = {chunk.id for chunk in result.scalars().all()}
        if len(found_chunks) != len(source_chunk_ids):
            missing = set(source_chunk_ids) - found_chunks
            raise ReferenceNotFoundError(f"Source chunks not found: {missing}")


async def validate_asset_job_create_request(
    world_id: UUID,
    asset_type: str,
    prompt_spec: dict,
    claim_ids: list[UUID],
    entity_ids: list[UUID],
    source_chunk_ids: list[UUID],
    source_id: UUID | None,
    session: AsyncSession,
    requested_by: str,
) -> None:
    """Validate a complete asset job creation request."""
    # Validate world exists
    await validate_world_exists(world_id, session)

    # Validate references exist
    await validate_references_exist(claim_ids, entity_ids, source_chunk_ids, session)

    # Validate world scoping
    await validate_world_scoping(
        world_id, claim_ids, entity_ids, source_chunk_ids, source_id, session
    )

    # Validate asset type
    valid_asset_types = ["VIDEO", "AUDIO", "IMAGE", "MAP", "PDF"]
    if asset_type not in valid_asset_types:
        raise BadRequestException(
            f"Invalid asset_type: {asset_type}. Must be one of {valid_asset_types}"
        )

    # Validate prompt spec is not empty
    if not prompt_spec or not isinstance(prompt_spec, dict):
        raise BadRequestException("prompt_spec must be a non-empty JSON object")


def validate_job_status_transition(current_status: str, new_status: str) -> None:
    """Validate that a job status transition is allowed."""
    valid_transitions = {
        "QUEUED": ["RUNNING", "CANCELLED"],
        "RUNNING": ["SUCCEEDED", "FAILED", "CANCELLED"],
        "SUCCEEDED": [],
        "FAILED": [],
        "CANCELLED": [],
    }

    if new_status not in valid_transitions.get(current_status, []):
        raise BadRequestException(
            f"Invalid status transition from {current_status} to {new_status}. "
            f"Valid transitions: {valid_transitions.get(current_status, [])}"
        )


async def validate_asset_authorization(
    requested_by: str,
    asset_id: UUID,
    session: AsyncSession,
) -> None:
    """Validate that a user is authorized to access an asset."""
    # For now, we allow any authenticated user to view any asset.
    # Future: implement world-level or user-level access controls.
    pass


async def validate_worker_authorization(worker_token: str | None) -> None:
    """Validate that a request is from an authorized worker."""
    # In a real implementation, this would validate the worker token against
    # a known list of worker credentials or JWT tokens.
    # For now, we just require the token to be present.
    if not worker_token:
        raise UnauthorizedException("Worker authentication required")
