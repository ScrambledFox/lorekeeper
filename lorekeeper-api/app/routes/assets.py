"""
Asset API routes for LoreKeeper.

Provides endpoints for:
- Asset job creation and management
- Asset retrieval
- Worker operations (job status updates, completion, failure)
- S3 presigned URL generation
"""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    BadRequestException,
    InternalServerErrorException,
    NotFoundException,
)
from app.db.database import get_async_session
from app.models.api.assets import (
    AssetJobCompleteRequest,
    AssetJobCreate,
    AssetJobFailRequest,
    AssetJobFullResponse,
    AssetJobUpdate,
    AssetResponse,
    PaginatedAssetJobResponse,
    PaginatedAssetResponse,
)
from app.models.api.s3 import (
    PresignedDownloadResponse,
    PresignedUploadRequest,
    PresignedUploadResponse,
)
from app.repositories.assets import AssetRepository
from app.services.asset_job_service import (
    build_idempotent_job_response,
    create_job_and_derivation,
    prepare_asset_job_inputs,
)
from app.services.asset_response_builder import build_full_job_response
from app.services.asset_s3_service import generate_download_url, generate_upload_url
from app.services.asset_worker_service import (
    complete_job,
    fail_job,
    get_worker_token,
    update_job_status,
)
from app.utils.asset_validation import (
    AssetValidationError,
    ReferenceNotFoundError,
    WorldNotFoundError,
    WorldScopeViolationError,
    validate_asset_authorization,
    validate_worker_authorization,
)

router = APIRouter(prefix="/assets", tags=["assets"])
asset_repo = AssetRepository()


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
        (
            claim_ids,
            entity_ids,
            source_chunk_ids,
            source_id,
            prompt_spec_dict,
            input_hash,
        ) = await prepare_asset_job_inputs(job, session, user_id)

        idempotent_response = await build_idempotent_job_response(
            asset_repo, session, job.world_id, input_hash
        )
        if idempotent_response:
            return idempotent_response

        return await create_job_and_derivation(
            asset_repo=asset_repo,
            session=session,
            job=job,
            requested_by=user_id,
            claim_ids=claim_ids,
            entity_ids=entity_ids,
            source_chunk_ids=source_chunk_ids,
            source_id=source_id,
            prompt_spec_dict=prompt_spec_dict,
            input_hash=input_hash,
        )

    except WorldNotFoundError as e:
        await session.rollback()
        raise NotFoundException(resource="World", id=str(e)) from e
    except ReferenceNotFoundError as e:
        await session.rollback()
        raise NotFoundException(resource="Reference", id=str(e)) from e
    except WorldScopeViolationError as e:
        await session.rollback()
        raise BadRequestException(message=str(e)) from e
    except AssetValidationError as e:
        await session.rollback()
        raise BadRequestException(message=str(e)) from e
    except Exception as e:
        await session.rollback()
        raise InternalServerErrorException(message=str(e)) from e


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

        return build_full_job_response(db_job, derivation, asset)
    except Exception as e:
        raise InternalServerErrorException(message=str(e)) from e


@router.get("/asset-jobs", response_model=PaginatedAssetJobResponse)
async def list_asset_jobs(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    world_id: UUID | None = Query(None),
    status: str | None = Query(None),
    asset_type: str | None = Query(None),
    provider: str | None = Query(None),
    requested_by: str | None = Query(None),
    created_after: datetime | None = Query(None),
    created_before: datetime | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
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
            items.append(build_full_job_response(job, derivation, asset_data))

        return PaginatedAssetJobResponse(total=total, skip=skip, limit=limit, items=items)
    except Exception as e:
        raise InternalServerErrorException(message=str(e)) from e


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

        return await update_job_status(asset_repo, session, job_id, update)

    except Exception as e:
        await session.rollback()
        raise InternalServerErrorException(message=str(e)) from e


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

        return await complete_job(asset_repo, session, job_id, request)

    except Exception as e:
        await session.rollback()
        raise InternalServerErrorException(message=str(e)) from e


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

        return await fail_job(
            asset_repo, session, job_id, request.error_code, request.error_message
        )

    except Exception as e:
        await session.rollback()
        raise InternalServerErrorException(message=str(e)) from e


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
        raise InternalServerErrorException(message=str(e)) from e


@router.get("/assets", response_model=PaginatedAssetResponse)
async def list_assets(
    session: Annotated[AsyncSession, Depends(get_async_session)],
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
        raise InternalServerErrorException(message=str(e)) from e


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
        return await generate_download_url(asset_repo, session, asset_id, user_id)
    except NotFoundException:
        raise
    except Exception as e:
        raise InternalServerErrorException(message=str(e)) from e


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
        return await generate_upload_url(
            session,
            request.world_id,
            request.asset_type,
            request.filename,
            request.content_type,
        )
    except NotFoundException:
        raise
    except Exception as e:
        raise InternalServerErrorException(message=str(e)) from e
