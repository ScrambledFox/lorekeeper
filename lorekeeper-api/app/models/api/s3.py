"""API models for S3 presigned URL operations."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class PresignedDownloadResponse(BaseModel):
    """Response for presigned download URL request."""

    asset_id: UUID = Field(..., description="Asset ID")
    presigned_url: str = Field(..., description="Presigned URL for downloading")
    expires_at: datetime = Field(..., description="When the presigned URL expires")


class PresignedUploadResponse(BaseModel):
    """Response for presigned upload URL request."""

    presigned_url: str = Field(..., description="Presigned URL for uploading")
    expires_at: datetime = Field(..., description="When the presigned URL expires")


class PresignedUploadRequest(BaseModel):
    """Request body for presigned upload URL generation."""

    world_id: UUID = Field(..., description="World ID for the asset")
    asset_type: str = Field(..., description="Asset type (VIDEO, AUDIO, etc.)")
    filename: str = Field(..., description="Filename for the asset")
    content_type: str = Field(..., description="MIME type of the file")
    file_size_bytes: int | None = Field(None, ge=1, description="File size in bytes (optional)")


class PresignedMultipartUploadResponse(BaseModel):
    """Response for initiating multipart upload."""

    upload_id: str = Field(..., description="Upload ID for tracking multipart upload")
    parts: list[dict] = Field(
        ...,
        description="List of presigned URLs for each part",
    )
    expires_at: datetime = Field(..., description="When the presigned URLs expire")


class CompleteMultipartUploadRequest(BaseModel):
    """Request body for completing multipart upload."""

    upload_id: str = Field(..., description="Upload ID from initiation")
    parts: list[dict] = Field(
        ...,
        description="List of completed parts with part_number and etag",
    )


class AbortMultipartUploadRequest(BaseModel):
    """Request body for aborting multipart upload."""

    upload_id: str = Field(..., description="Upload ID to abort")
