"""Worker utilities for asset job operations.

Provides utilities for worker authentication and job status management,
separating worker-specific logic from main route handlers.
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api.assets import AssetJobCompleteRequest, AssetJobFullResponse, AssetJobUpdate
from app.repositories.assets import AssetRepository
from app.services.asset_response_builder import build_full_job_response
from app.utils.asset_validation import validate_worker_authorization, validate_job_status_transition
from datetime import datetime


def get_worker_token(authorization: str | None) -> str | None:
    """Extract and validate worker token from Authorization header.

    Args:
        authorization: Authorization header value

    Returns:
        Bearer token string if valid Bearer token found, None otherwise
    """
    if authorization and authorization.startswith("Bearer "):
        return authorization[7:]
    return None


async def update_job_status(
    asset_repo: AssetRepository,
    session: AsyncSession,
    job_id: UUID,
    update: AssetJobUpdate,
) -> AssetJobFullResponse:
    """Update an asset job's status and metadata.

    Args:
        asset_repo: Asset repository instance
        session: Database session
        job_id: UUID of the job to update
        update: Status update data

    Returns:
        Full response of the updated job
    """
    # Get existing job
    db_job = await asset_repo.get_asset_job(session, job_id)
    if not db_job:
        from app.core.exceptions import NotFoundException

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

    return build_full_job_response(updated_job, derivation, asset)


async def complete_job(
    asset_repo: AssetRepository,
    session: AsyncSession,
    job_id: UUID,
    request: AssetJobCompleteRequest,
) -> AssetJobFullResponse:
    """Complete an asset job with asset data.

    This operation:
    1. Creates the Asset record
    2. Updates the job status to SUCCEEDED
    3. Links the asset to the derivation

    Args:
        asset_repo: Asset repository instance
        session: Database session
        job_id: UUID of the job to complete
        request: Completion request with asset data

    Returns:
        Full response of the completed job with asset
    """
    # Get existing job
    db_job = await asset_repo.get_asset_job(session, job_id)
    if not db_job:
        from app.core.exceptions import NotFoundException

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

    return build_full_job_response(db_job, derivation, asset)


async def fail_job(
    asset_repo: AssetRepository,
    session: AsyncSession,
    job_id: UUID,
    error_code: str,
    error_message: str,
) -> AssetJobFullResponse:
    """Mark an asset job as failed with error details.

    Args:
        asset_repo: Asset repository instance
        session: Database session
        job_id: UUID of the job to fail
        error_code: Error code identifier
        error_message: Human-readable error message

    Returns:
        Full response of the failed job
    """
    # Get existing job
    db_job = await asset_repo.get_asset_job(session, job_id)
    if not db_job:
        from app.core.exceptions import NotFoundException

        raise NotFoundException(resource="AssetJob", id=str(job_id))

    # Update job status
    db_job = await asset_repo.update_asset_job_status(
        session=session,
        job_id=job_id,
        status="FAILED",
        finished_at=datetime.utcnow(),
        error_code=error_code,
        error_message=error_message,
    )

    await session.commit()

    derivation = await asset_repo.get_derivation_by_job_id(session, job_id)
    return build_full_job_response(db_job, derivation, None)
