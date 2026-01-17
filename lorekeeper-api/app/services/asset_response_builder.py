"""Asset response builder for constructing API responses."""

from typing import Any

from app.models.api.assets import (
    AssetDerivationResponse,
    AssetJobFullResponse,
    AssetJobReferences,
    AssetJobResponse,
    AssetResponse,
)


def build_full_job_response(job: Any, derivation: Any, asset: Any) -> AssetJobFullResponse:
    """Build a full job response with derivation and asset.

    Constructs a complete AssetJobFullResponse from job, derivation, and asset objects,
    handling relationship loading and null cases gracefully.

    Args:
        job: The asset job database object
        derivation: The asset derivation database object (optional)
        asset: The asset database object (optional)

    Returns:
        AssetJobFullResponse with all nested data populated
    """
    # Use model_construct to avoid any ORM access
    job_data_dict = {
        "id": job.id,
        "world_id": job.world_id,
        "asset_type": job.asset_type,
        "provider": job.provider,
        "model_id": job.model_id,
        "status": job.status,
        "priority": job.priority,
        "requested_by": job.requested_by,
        "input_hash": job.input_hash,
        "prompt_spec": job.prompt_spec,
        "error_code": job.error_code,
        "error_message": job.error_message,
        "created_at": job.created_at,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
    }
    job_data = AssetJobResponse.model_construct(**job_data_dict)

    derivation_data = None
    if derivation:
        # Eagerly access relationships to force loading while session is active
        try:
            claim_ids = [claim.claim_id for claim in (derivation.claims or [])]
            entity_ids = [entity.entity_id for entity in (derivation.entities or [])]
            source_chunk_ids = [chunk.source_chunk_id for chunk in (derivation.source_chunks or [])]
        except Exception:
            # Fallback if relationships can't be loaded
            claim_ids = []
            entity_ids = []
            source_chunk_ids = []

        derivation_data = AssetDerivationResponse(
            id=derivation.id,
            asset_job_id=derivation.asset_job_id,
            asset_id=derivation.asset_id,
            source_id=derivation.source_id,
            prompt_spec=derivation.prompt_spec,
            input_hash=derivation.input_hash,
            lore_snapshot=derivation.lore_snapshot,
            created_at=derivation.created_at,
            references=AssetJobReferences(
                claim_ids=claim_ids,
                entity_ids=entity_ids,
                source_chunk_ids=source_chunk_ids,
                source_id=derivation.source_id,
            ),
        )

    asset_data = None
    if asset:
        asset_data_dict = {
            "id": asset.id,
            "world_id": asset.world_id,
            "type": asset.type,
            "format": asset.format,
            "status": asset.status,
            "storage_key": asset.storage_key,
            "content_type": asset.content_type,
            "duration_seconds": asset.duration_seconds,
            "size_bytes": asset.size_bytes,
            "checksum": asset.checksum,
            "meta": asset.meta,
            "created_by": asset.created_by,
            "created_at": asset.created_at,
        }
        asset_data = AssetResponse.model_construct(**asset_data_dict)

    return AssetJobFullResponse(
        **job_data.model_dump(),
        derivation=derivation_data,
        asset=asset_data,
    )
