"""Asset job service for handling asset creation and job operations."""

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api.assets import AssetJobCreate, AssetJobFullResponse
from app.repositories.assets import AssetRepository
from app.services.asset_response_builder import build_full_job_response
from app.utils.asset_validation import validate_asset_job_create_request
from app.utils.hashing import compute_input_hash, extract_uuids_from_references


async def create_lore_snapshot(derivation_data: dict) -> dict | None:
    """Create a lore snapshot from references.

    This is a simplified version. In a real implementation,
    we would fetch the actual lore entities and snapshot them.

    Args:
        derivation_data: Dictionary containing reference IDs

    Returns:
        Snapshot dictionary with serialized IDs, or None if no data
    """
    if not derivation_data:
        return None

    return {
        "claim_ids": [str(cid) for cid in derivation_data.get("claim_ids", [])],
        "entity_ids": [str(eid) for eid in derivation_data.get("entity_ids", [])],
        "source_chunk_ids": [str(scid) for scid in derivation_data.get("source_chunk_ids", [])],
    }


def normalize_prompt_spec(prompt_spec: Any) -> dict:
    """Normalize prompt spec to dictionary format.

    Args:
        prompt_spec: Either a dict or a Pydantic model

    Returns:
        Dictionary representation of prompt spec
    """
    if isinstance(prompt_spec, dict):
        return prompt_spec
    return prompt_spec.model_dump()


async def prepare_asset_job_inputs(
    job: AssetJobCreate,
    session: AsyncSession,
    requested_by: str,
) -> tuple[list[UUID], list[UUID], list[UUID], UUID | None, dict, str]:
    """Prepare and validate asset job inputs.

    Extracts UUIDs from references, validates the job request, and computes
    an input hash for idempotency checking.

    Args:
        job: The asset job creation request
        session: Database session
        requested_by: User ID requesting the job

    Returns:
        Tuple of (claim_ids, entity_ids, source_chunk_ids, source_id, prompt_spec_dict, input_hash)

    Raises:
        Various validation errors (see validate_asset_job_create_request)
    """
    claim_ids, entity_ids, source_chunk_ids, source_id = extract_uuids_from_references(
        job.references.model_dump()
    )

    prompt_spec_dict = normalize_prompt_spec(job.prompt_spec)

    await validate_asset_job_create_request(
        world_id=job.world_id,
        asset_type=job.asset_type,
        prompt_spec=prompt_spec_dict,
        claim_ids=claim_ids,
        entity_ids=entity_ids,
        source_chunk_ids=source_chunk_ids,
        source_id=source_id,
        session=session,
        requested_by=requested_by,
    )

    input_hash = compute_input_hash(
        prompt_spec=prompt_spec_dict,
        world_id=job.world_id,
        asset_type=job.asset_type,
        provider=job.provider,
        model_id=job.model_id,
        claim_ids=claim_ids,
        entity_ids=entity_ids,
        source_chunk_ids=source_chunk_ids,
        source_id=source_id,
    )

    return claim_ids, entity_ids, source_chunk_ids, source_id, prompt_spec_dict, input_hash


async def build_idempotent_job_response(
    asset_repo: AssetRepository,
    session: AsyncSession,
    world_id: UUID,
    input_hash: str,
) -> AssetJobFullResponse | None:
    """Check for and return an existing job matching the input hash.

    This enables idempotency - if the same request is made twice, the same
    job is returned instead of creating a duplicate.

    Args:
        asset_repo: Asset repository instance
        session: Database session
        world_id: World ID for the request
        input_hash: Hash of job inputs

    Returns:
        Existing job response if found and not failed, None otherwise
    """
    existing_job = await asset_repo.get_asset_job_by_input_hash(session, world_id, input_hash)
    if not existing_job or existing_job.status == "FAILED":
        return None

    derivation = await asset_repo.get_derivation_by_job_id(session, existing_job.id)
    # Access asset while session is active before passing to response builder
    asset = None
    if derivation:
        # Eagerly access the asset relationship while in async context
        try:
            asset = derivation.asset
        except Exception:
            asset = None

    return build_full_job_response(existing_job, derivation, asset)


async def create_job_and_derivation(
    asset_repo: AssetRepository,
    session: AsyncSession,
    job: AssetJobCreate,
    requested_by: str,
    claim_ids: list[UUID],
    entity_ids: list[UUID],
    source_chunk_ids: list[UUID],
    source_id: UUID | None,
    prompt_spec_dict: dict,
    input_hash: str,
) -> AssetJobFullResponse:
    """Create a new asset job and its derivation.

    Creates both the job record and the derivation record, linking all
    referenced claims, entities, and source chunks.

    Args:
        asset_repo: Asset repository instance
        session: Database session
        job: The asset job creation request
        requested_by: User ID requesting the job
        claim_ids: List of claim UUIDs referenced
        entity_ids: List of entity UUIDs referenced
        source_chunk_ids: List of source chunk UUIDs referenced
        source_id: Optional source UUID referenced
        prompt_spec_dict: Normalized prompt specification
        input_hash: Hash of job inputs for idempotency

    Returns:
        Full job response with derivation
    """
    db_job = await asset_repo.create_asset_job(
        session=session,
        job=job,
        requested_by=requested_by,
        input_hash=input_hash,
    )

    lore_snapshot = await create_lore_snapshot(job.references.model_dump())

    derivation = await asset_repo.create_asset_derivation(
        session=session,
        asset_job_id=db_job.id,
        world_id=job.world_id,
        prompt_spec=prompt_spec_dict,
        input_hash=input_hash,
        lore_snapshot=lore_snapshot,
        source_id=source_id,
    )

    if claim_ids:
        await asset_repo.add_derivation_claims(session, derivation.id, claim_ids)
    if entity_ids:
        await asset_repo.add_derivation_entities(session, derivation.id, entity_ids)
    if source_chunk_ids:
        await asset_repo.add_derivation_source_chunks(session, derivation.id, source_chunk_ids)

    await session.flush()
    derivation = await asset_repo.get_derivation_by_job_id(session, db_job.id)
    await session.commit()

    return build_full_job_response(db_job, derivation, None)
