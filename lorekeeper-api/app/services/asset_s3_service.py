"""S3 presigned URL utilities for asset operations."""

import time
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.models.api.s3 import PresignedDownloadResponse, PresignedUploadResponse
from app.models.db.worlds import World
from app.repositories.assets import AssetRepository
from app.utils.asset_validation import validate_asset_authorization
from app.utils.s3 import get_s3_client


async def generate_download_url(
    asset_repo: AssetRepository,
    session: AsyncSession,
    asset_id: UUID,
    user_id: str,
) -> PresignedDownloadResponse:
    """Generate a presigned URL for downloading an asset from S3.

    This endpoint returns a URL that can be used to download the asset without
    additional authentication. The URL expires after a configured time period.

    Args:
        asset_repo: Asset repository instance
        session: Database session
        asset_id: UUID of the asset to download
        user_id: User ID requesting the download

    Returns:
        Response with presigned URL and expiration time

    Raises:
        NotFoundException: If asset not found or user not authorized
    """
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


async def generate_upload_url(
    session: AsyncSession,
    world_id: UUID,
    asset_type: str,
    filename: str,
    content_type: str,
) -> PresignedUploadResponse:
    """Generate a presigned URL for uploading a file to S3.

    This endpoint is used before creating an asset job to get a URL for uploading
    the media file directly to S3. After upload completes, use the storage_key
    in the asset creation request.

    Args:
        session: Database session
        world_id: UUID of the world where asset will be stored
        asset_type: Type of asset being uploaded
        filename: Original filename
        content_type: MIME type of the file

    Returns:
        Response with presigned upload URL and expiration time

    Raises:
        NotFoundException: If world not found
    """
    # Validate world exists
    result = await session.execute(select(World).where(World.id == world_id))
    if not result.scalars().first():
        raise NotFoundException(resource="World", id=str(world_id))

    # Generate a storage key based on world, type, and filename
    # Format: world_id/asset_type/timestamp_filename
    timestamp = int(time.time() * 1000)
    storage_key = f"{world_id}/{asset_type.lower()}/{timestamp}_{filename}"

    # Generate presigned URL
    s3_client = get_s3_client()
    presigned_url = s3_client.generate_upload_presigned_url(storage_key, content_type=content_type)

    return PresignedUploadResponse(
        presigned_url=presigned_url,
        expires_at=datetime.utcnow() + timedelta(seconds=s3_client.expiry_seconds),
    )
