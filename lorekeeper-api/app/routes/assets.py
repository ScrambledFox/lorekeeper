"""
Asset API routes for LoreKeeper.

Provides endpoints for:
- Asset job creation and management
- Asset retrieval
- Worker operations (job status updates, completion, failure)
"""

from typing import Annotated, Any
from datetime import datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    BadRequestException,
    InternalServerErrorException,
    NotFoundException,
    UnauthorizedException,
)
from app.db.database import get_async_session
from app.models.api.assets import (
    AssetCreate,
    AssetJobCompleteRequest,
    AssetJobCreate,
    AssetJobFailRequest,
    AssetJobFullResponse,
    AssetJobListFilter,
    AssetJobResponse,
    AssetJobUpdate,
    AssetListFilter,
    AssetResponse,
    PaginatedAssetJobResponse,
    PaginatedAssetResponse,
    AssetDerivationResponse,
    AssetJobReferences,
)
from app.models.api.s3 import (
    PresignedDownloadResponse,
    PresignedUploadResponse,
    PresignedUploadRequest,
)
from app.repositories.assets import AssetRepository
from app.utils.asset_validation import (
    AssetValidationError,
    ReferenceNotFoundError,
    WorldNotFoundError,
    WorldScopeViolationError,
    validate_asset_job_create_request,
    validate_job_status_transition,
    validate_worker_authorization,
    validate_asset_authorization,
)
from app.utils.hashing import (
    compute_input_hash,
    extract_uuids_from_references,
)
from app.utils.s3 import get_s3_client
from app.db.database import get_async_session
from app.models.api.assets import (
    AssetCreate,
    AssetJobCompleteRequest,
    AssetJobCreate,
    AssetJobFailRequest,
    AssetJobFullResponse,
    AssetJobListFilter,
    AssetJobResponse,
    AssetJobUpdate,
    AssetListFilter,
    AssetResponse,
    PaginatedAssetJobResponse,
    PaginatedAssetResponse,
    AssetDerivationResponse,
    AssetJobReferences,
)
from app.repositories.assets import AssetRepository
from app.utils.asset_validation import (
    AssetValidationError,
    ReferenceNotFoundError,
    WorldNotFoundError,
    WorldScopeViolationError,
    validate_asset_job_create_request,
    validate_job_status_transition,
    validate_worker_authorization,
    validate_asset_authorization,
)
from app.utils.hashing import (
    compute_input_hash,
    extract_uuids_from_references,
)

router = APIRouter(prefix="/assets", tags=["assets"])
asset_repo = AssetRepository()

# ==================== Helper Functions ====================


def get_worker_token(authorization: str | None = Header(None)) -> str | None:
    """Extract and validate worker token from Authorization header."""
    if authorization and authorization.startswith("Bearer "):
        return authorization[7:]
    return None


async def create_lore_snapshot(
    derivation_data: dict,
) -> dict | None:
    """Create a lore snapshot from references."""
    # This is a simplified version. In a real implementation,
    # we would fetch the actual lore entities and snapshot them.
    if not derivation_data:
        return None

    return {
        "claim_ids": [str(cid) for cid in derivation_data.get("claim_ids", [])],
        "entity_ids": [str(eid) for eid in derivation_data.get("entity_ids", [])],
        "source_chunk_ids": [str(scid) for scid in derivation_data.get("source_chunk_ids", [])],
    }


# ==================== Asset Job Endpoints ====================


@router.post(
    "/asset-jobs", response_model=AssetJobFullResponse, status_code=status.HTTP_201_CREATED
)
async def create_asset_job(
    job: AssetJobCreate,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user_id: str = Header(..., description="User ID"),
) -> AssetJobFullResponse:
    """
    Create a new asset job.

    This endpoint is used to request generation of a multimodal asset (video, audio, etc.).
    The system will check for idempotency based on input_hash and return existing job/asset if found.

    Returns:
    - New AssetJob with QUEUED status, or
    - Existing job/asset if idempotent request
    """
    try:
        # Extract reference IDs
        claim_ids, entity_ids, source_chunk_ids, source_id = extract_uuids_from_references(
            job.references.model_dump()
        )

        # Validate the request
        await validate_asset_job_create_request(
            world_id=job.world_id,
            asset_type=job.asset_type,
            prompt_spec=job.prompt_spec
            if isinstance(job.prompt_spec, dict)
            else job.prompt_spec.model_dump(),
            claim_ids=claim_ids,
            entity_ids=entity_ids,
            source_chunk_ids=source_chunk_ids,
            source_id=source_id,
            session=session,
            requested_by=user_id,
        )

        # Compute input hash
        input_hash = compute_input_hash(
            prompt_spec=job.prompt_spec
            if isinstance(job.prompt_spec, dict)
            else job.prompt_spec.model_dump(),
            world_id=job.world_id,
            asset_type=job.asset_type,
            provider=job.provider,
            model_id=job.model_id,
            claim_ids=claim_ids,
            entity_ids=entity_ids,
            source_chunk_ids=source_chunk_ids,
            source_id=source_id,
        )

        # Check for idempotency
        existing_job = await asset_repo.get_asset_job_by_input_hash(
            session, job.world_id, input_hash
        )
        if existing_job:
            # Return existing job if found and not in failed state
            if existing_job.status != "FAILED":
                derivation = await asset_repo.get_derivation_by_job_id(session, existing_job.id)
                asset = derivation.asset if derivation else None
                return _build_full_job_response(existing_job, derivation, asset)

        # Create new job
        db_job = await asset_repo.create_asset_job(
            session=session,
            job=job,
            requested_by=user_id,
            input_hash=input_hash,
        )

        # Create derivation
        prompt_spec_dict = (
            job.prompt_spec if isinstance(job.prompt_spec, dict) else job.prompt_spec.model_dump()
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

        # Add reference links
        if claim_ids:
            await asset_repo.add_derivation_claims(session, derivation.id, claim_ids)
        if entity_ids:
            await asset_repo.add_derivation_entities(session, derivation.id, entity_ids)
        if source_chunk_ids:
            await asset_repo.add_derivation_source_chunks(session, derivation.id, source_chunk_ids)

        # Flush to persist joins before reloading
        await session.flush()

        # Reload derivation with all relationships before commit
        derivation = await asset_repo.get_derivation_by_job_id(session, db_job.id)

        # Commit transaction
        await session.commit()

        # Publish job to queue (placeholder for async job dispatch)
        # TODO: Publish to job queue for worker processing

        return _build_full_job_response(db_job, derivation, None)

    except WorldNotFoundError as e:
        await session.rollback()
        raise NotFoundException(resource="World", id=str(e))
    except ReferenceNotFoundError as e:
        await session.rollback()
        raise NotFoundException(resource="Reference", id=str(e))
    except WorldScopeViolationError as e:
        await session.rollback()
        raise BadRequestException(message=str(e))
    except AssetValidationError as e:
        await session.rollback()
        raise BadRequestException(message=str(e))
    except Exception as e:
        await session.rollback()
        raise InternalServerErrorException(message=str(e))


@router.get("/asset-jobs/{job_id}", response_model=AssetJobFullResponse)
async def get_asset_job(
    job_id: UUID,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> AssetJobFullResponse:
    """Get an asset job by ID."""
    try:
        db_job = await asset_repo.get_asset_job(session, job_id)
        if not db_job:
            raise NotFoundException(resource="AssetJob", id=str(job_id))

        derivation = await asset_repo.get_derivation_by_job_id(session, job_id)
        asset = derivation.asset if derivation else None

        return _build_full_job_response(db_job, derivation, asset)
    except Exception as e:
        raise InternalServerErrorException(message=str(e))


@router.get("/asset-jobs", response_model=PaginatedAssetJobResponse)
async def list_asset_jobs(
    world_id: UUID | None = Query(None),
    status: str | None = Query(None),
    asset_type: str | None = Query(None),
    provider: str | None = Query(None),
    requested_by: str | None = Query(None),
    created_after: datetime | None = Query(None),
    created_before: datetime | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    session: Annotated[AsyncSession, Depends(get_async_session)] = None,
) -> PaginatedAssetJobResponse:
    """List asset jobs with optional filtering."""
    try:
        jobs, total = await asset_repo.list_asset_jobs(
            session=session,
            world_id=world_id,
            status=status,
            asset_type=asset_type,
            provider=provider,
            requested_by=requested_by,
            created_after=created_after,
            created_before=created_before,
            skip=skip,
            limit=limit,
        )

        # Build items without await in list comprehension
        items = []
        for job in jobs:
            derivation = await asset_repo.get_derivation_by_job_id(session, job.id)
            asset_data = derivation.asset if derivation else None
            items.append(_build_full_job_response(job, derivation, asset_data))

        return PaginatedAssetJobResponse(total=total, skip=skip, limit=limit, items=items)
    except Exception as e:
        raise InternalServerErrorException(message=str(e))


# ==================== Worker Operations ====================


@router.patch("/asset-jobs/{job_id}", response_model=AssetJobFullResponse)
async def update_asset_job_status(
    job_id: UUID,
    update: AssetJobUpdate,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    authorization: Annotated[str | None, Header()] = None,
) -> AssetJobFullResponse:
    """
    Update an asset job's status (worker only).

    Workers use this to transition job status through the pipeline:
    QUEUED -> RUNNING -> SUCCEEDED/FAILED/CANCELLED
    """
    try:
        # Validate worker authorization
        worker_token = get_worker_token(authorization)
        await validate_worker_authorization(worker_token)

        # Get existing job
        db_job = await asset_repo.get_asset_job(session, job_id)
        if not db_job:
            raise NotFoundException(resource="AssetJob", id=str(job_id))

        # Validate status transition
        if update.status:
            validate_job_status_transition(db_job.status, update.status)

        # Update job
        updated_job = await asset_repo.update_asset_job_status(
            session=session,
            job_id=job_id,
            status=update.status or db_job.status,
            started_at=update.started_at,
            finished_at=update.finished_at,
            error_code=update.error_code,
            error_message=update.error_message,
        )

        await session.commit()

        derivation = await asset_repo.get_derivation_by_job_id(session, job_id)
        asset = derivation.asset if derivation else None

        return _build_full_job_response(updated_job, derivation, asset)
    except Exception as e:
        await session.rollback()
        raise InternalServerErrorException(message=str(e))


@router.post("/asset-jobs/{job_id}/complete", response_model=AssetJobFullResponse)
async def complete_asset_job(
    job_id: UUID,
    request: AssetJobCompleteRequest,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    authorization: Annotated[str | None, Header()] = None,
) -> AssetJobFullResponse:
    """
    Complete an asset job with asset data (worker only).

    This endpoint:
    1. Creates the Asset record
    2. Updates the job status to SUCCEEDED
    3. Links the asset to the derivation
    """
    try:
        # Validate worker authorization
        worker_token = get_worker_token(authorization)
        await validate_worker_authorization(worker_token)

        # Get existing job
        db_job = await asset_repo.get_asset_job(session, job_id)
        if not db_job:
            raise NotFoundException(resource="AssetJob", id=str(job_id))

        # Create asset
        asset = await asset_repo.create_asset(session, request.asset)

        # Update job status
        db_job = await asset_repo.update_asset_job_status(
            session=session,
            job_id=job_id,
            status="SUCCEEDED",
            finished_at=datetime.utcnow(),
        )

        # Update derivation to link asset
        derivation = await asset_repo.get_derivation_by_job_id(session, job_id)
        if derivation:
            await asset_repo.update_derivation_asset_id(session, derivation.id, asset.id)

        await session.commit()

        return _build_full_job_response(db_job, derivation, asset)
    except Exception as e:
        await session.rollback()
        raise InternalServerErrorException(message=str(e))


@router.post("/asset-jobs/{job_id}/fail", response_model=AssetJobFullResponse)
async def fail_asset_job(
    job_id: UUID,
    request: AssetJobFailRequest,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    authorization: Annotated[str | None, Header()] = None,
) -> AssetJobFullResponse:
    """
    Mark an asset job as failed (worker only).
    """
    try:
        # Validate worker authorization
        worker_token = get_worker_token(authorization)
        await validate_worker_authorization(worker_token)

        # Get existing job
        db_job = await asset_repo.get_asset_job(session, job_id)
        if not db_job:
            raise NotFoundException(resource="AssetJob", id=str(job_id))

        # Update job status
        db_job = await asset_repo.update_asset_job_status(
            session=session,
            job_id=job_id,
            status="FAILED",
            finished_at=datetime.utcnow(),
            error_code=request.error_code,
            error_message=request.error_message,
        )

        await session.commit()

        derivation = await asset_repo.get_derivation_by_job_id(session, job_id)
        return _build_full_job_response(db_job, derivation, None)
    except Exception as e:
        await session.rollback()
        raise InternalServerErrorException(message=str(e))


# ==================== Asset Endpoints ====================


@router.get("/assets/{asset_id}", response_model=AssetResponse)
async def get_asset(
    asset_id: UUID,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user_id: str = Header(...),
) -> AssetResponse:
    """Get an asset by ID."""
    try:
        # Validate authorization
        await validate_asset_authorization(user_id, asset_id, session)

        asset = await asset_repo.get_asset(session, asset_id)
        if not asset:
            raise NotFoundException(resource="Asset", id=str(asset_id))

        return AssetResponse.model_validate(asset, from_attributes=True)
    except Exception as e:
        raise InternalServerErrorException(message=str(e))


@router.get("/assets", response_model=PaginatedAssetResponse)
async def list_assets(
    world_id: UUID | None = Query(None),
    asset_type: str | None = Query(None),
    status: str | None = Query(None),
    created_by: str | None = Query(None),
    related_claim_id: UUID | None = Query(None),
    related_entity_id: UUID | None = Query(None),
    related_source_chunk_id: UUID | None = Query(None),
    source_id: UUID | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    session: Annotated[AsyncSession, Depends(get_async_session)] = None,
    user_id: str = Header(...),
) -> PaginatedAssetResponse:
    """List assets with optional filtering."""
    try:
        assets, total = await asset_repo.list_assets(
            session=session,
            world_id=world_id,
            asset_type=asset_type,
            status=status,
            created_by=created_by,
            related_claim_id=related_claim_id,
            related_entity_id=related_entity_id,
            related_source_chunk_id=related_source_chunk_id,
            source_id=source_id,
            skip=skip,
            limit=limit,
        )

        items = [AssetResponse.model_validate(asset, from_attributes=True) for asset in assets]
        return PaginatedAssetResponse(total=total, skip=skip, limit=limit, items=items)
    except Exception as e:
        raise InternalServerErrorException(message=str(e))


# ==================== Helper Functions ====================


def _build_full_job_response(job: Any, derivation: Any, asset: Any) -> AssetJobFullResponse:
    """Build a full job response with derivation and asset."""
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


# ==================== S3 Presigned URL Endpoints ====================


@router.post("/assets/{asset_id}/presign-download", response_model=PresignedDownloadResponse)
async def presign_download_url(
    asset_id: UUID,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user_id: str = Header(..., description="User ID"),
) -> PresignedDownloadResponse:
    """
    Generate a presigned URL for downloading an asset from S3.

    This endpoint returns a URL that can be used to download the asset without
    additional authentication. The URL expires after a configured time period.
    """
    try:
        # Get the asset
        asset = await asset_repo.get_asset(session, asset_id)
        if not asset:
            raise NotFoundException(resource="Asset", id=str(asset_id))

        # Validate authorization
        await validate_asset_authorization(user_id, asset_id, session)

        # Generate presigned URL
        s3_client = get_s3_client()
        presigned_url = s3_client.generate_download_presigned_url(asset.storage_key)

        return PresignedDownloadResponse(
            asset_id=asset_id,
            presigned_url=presigned_url,
            expires_at=datetime.utcnow() + timedelta(seconds=s3_client.expiry_seconds),
        )
    except NotFoundException:
        raise
    except Exception as e:
        raise InternalServerErrorException(message=str(e))


@router.post("/assets/presign-upload", response_model=PresignedUploadResponse)
async def presign_upload_url(
    request: PresignedUploadRequest,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user_id: str = Header(..., description="User ID"),
) -> PresignedUploadResponse:
    """
    Generate a presigned URL for uploading a file to S3.

    This endpoint is used before creating an asset job to get a URL for uploading
    the media file directly to S3. After upload completes, use the storage_key
    in the asset creation request.

    Returns a presigned URL valid for the configured time period (typically 1 hour).
    """
    try:
        # Validate world exists
        from app.models.db.worlds import World

        result = await session.execute(select(World).where(World.id == request.world_id))
        if not result.scalars().first():
            raise NotFoundException(resource="World", id=str(request.world_id))

        # Generate a storage key based on world, type, and filename
        # Format: world_id/asset_type/timestamp_filename
        import time

        timestamp = int(time.time() * 1000)
        storage_key = (
            f"{request.world_id}/{request.asset_type.lower()}/{timestamp}_{request.filename}"
        )

        # Generate presigned URL
        s3_client = get_s3_client()
        presigned_url = s3_client.generate_upload_presigned_url(
            storage_key, content_type=request.content_type
        )

        return PresignedUploadResponse(
            presigned_url=presigned_url,
            expires_at=datetime.utcnow() + timedelta(seconds=s3_client.expiry_seconds),
        )
    except NotFoundException:
        raise
    except Exception as e:
        raise InternalServerErrorException(message=str(e))
