"""API models for asset domain objects."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ==================== Enum-like Classes ====================


class AssetTypeEnum(str):
    """Asset type enumeration."""

    VIDEO = "VIDEO"
    AUDIO = "AUDIO"
    IMAGE = "IMAGE"
    MAP = "MAP"
    PDF = "PDF"


class AssetStatusEnum(str):
    """Asset status enumeration."""

    READY = "READY"
    FAILED = "FAILED"
    DELETED = "DELETED"


class AssetJobStatusEnum(str):
    """Asset job status enumeration."""

    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


# ==================== Asset Models ====================


class AssetMetadata(BaseModel):
    """Asset metadata (resolution, bitrate, codec, etc.)."""

    resolution: str | None = Field(None, description="Video resolution (e.g., 1920x1080)")
    bitrate: str | None = Field(None, description="Bitrate (e.g., 5000k)")
    codec: str | None = Field(None, description="Video/audio codec")
    thumbnail_key: str | None = Field(None, description="S3 key for thumbnail")
    duration: float | None = Field(None, description="Duration in seconds")
    extra: dict | None = Field(None, description="Additional custom metadata")


class AssetBase(BaseModel):
    """Base asset schema."""

    world_id: UUID = Field(..., description="World unique identifier")
    type: str = Field(..., description="Asset type (VIDEO, AUDIO, IMAGE, MAP, PDF)")
    format: str = Field(..., description="File format (e.g., mp4, wav)")
    storage_key: str = Field(..., description="S3 storage key")
    content_type: str = Field(..., description="MIME type")
    duration_seconds: int | None = Field(None, description="Duration in seconds for media")
    size_bytes: int | None = Field(None, description="File size in bytes")
    checksum: str | None = Field(None, description="File checksum")
    metadata: AssetMetadata | None = Field(None, description="Additional metadata")


class AssetCreate(AssetBase):
    """Schema for creating an asset (typically called by workers)."""

    created_by: str = Field(..., description="User/worker ID who created the asset")


class AssetResponse(AssetBase):
    """Schema for asset responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Asset unique identifier")
    status: str = Field(..., description="Asset status (READY, FAILED, DELETED)")
    created_by: str = Field(..., description="User/worker who created the asset")
    created_at: datetime = Field(..., description="Creation timestamp")


# ==================== Asset Job Models ====================


class PromptSpec(BaseModel):
    """Base prompt specification (provider-specific schemas extend this)."""

    model_config = ConfigDict(extra="allow")
    pass


class VideoPromptSpec(PromptSpec):
    """Prompt specification for video generation (Sora)."""

    description: str = Field(..., description="Video description/prompt")
    duration: int | None = Field(None, ge=1, le=120, description="Video duration in seconds")
    aspect_ratio: str | None = Field(None, description="Aspect ratio (e.g., 16:9, 9:16)")
    quality: str | None = Field(None, description="Quality level (e.g., standard, high)")


class AudioPromptSpec(PromptSpec):
    """Prompt specification for audio generation."""

    lyrics: str = Field(..., description="Lyrics or audio description")
    style: str | None = Field(None, description="Audio style (e.g., epic, ambient)")
    duration: int | None = Field(None, ge=1, le=600, description="Audio duration in seconds")
    tempo: str | None = Field(None, description="Tempo (e.g., slow, medium, fast)")


class AssetJobBase(BaseModel):
    """Base asset job schema."""

    world_id: UUID = Field(..., description="World unique identifier")
    asset_type: str = Field(..., description="Asset type to generate")
    provider: str = Field(..., description="Provider (e.g., sora, audio_model_x)")
    model_id: str | None = Field(None, description="Model ID on provider")
    prompt_spec: dict | PromptSpec = Field(..., description="Provider-specific prompt spec")
    priority: int | None = Field(None, ge=0, description="Job priority (higher = more urgent)")


class AssetJobReferences(BaseModel):
    """References to lore inputs for an asset job."""

    claim_ids: list[UUID] = Field(default_factory=list, description="Related claim IDs")
    entity_ids: list[UUID] = Field(default_factory=list, description="Related entity IDs")
    source_chunk_ids: list[UUID] = Field(
        default_factory=list, description="Related source chunk IDs"
    )
    source_id: UUID | None = Field(None, description="Related source ID")


class AssetJobCreate(AssetJobBase):
    """Schema for creating an asset job."""

    references: AssetJobReferences = Field(default_factory=lambda: AssetJobReferences())
    idempotency_key: str | None = Field(None, description="Optional idempotency key")


class AssetJobUpdate(BaseModel):
    """Schema for updating an asset job (worker operations)."""

    status: str | None = Field(None, description="New job status")
    started_at: datetime | None = Field(None, description="When job started")
    finished_at: datetime | None = Field(None, description="When job finished")
    error_code: str | None = Field(None, description="Error code if failed")
    error_message: str | None = Field(None, description="Error message if failed")


class AssetJobResponse(AssetJobBase):
    """Schema for asset job responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Job unique identifier")
    status: str = Field(..., description="Job status")
    requested_by: str = Field(..., description="User who requested the job")
    input_hash: str = Field(..., description="Idempotency hash")
    error_code: str | None = Field(None, description="Error code if failed")
    error_message: str | None = Field(None, description="Error message if failed")
    created_at: datetime = Field(..., description="Creation timestamp")
    started_at: datetime | None = Field(None, description="Started timestamp")
    finished_at: datetime | None = Field(None, description="Finished timestamp")


# ==================== Asset Derivation Models ====================


class LoreSnapshot(BaseModel):
    """Snapshot of lore inputs at time of derivation (for reproducibility)."""

    claim_snapshots: list[dict] = Field(
        default_factory=list, description="Snapshots of referenced claims"
    )
    entity_snapshots: list[dict] = Field(
        default_factory=list, description="Snapshots of referenced entities"
    )
    source_chunk_snapshots: list[dict] = Field(
        default_factory=list, description="Snapshots of referenced source chunks"
    )


class AssetDerivationResponse(BaseModel):
    """Schema for asset derivation responses (provenance info)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Derivation unique identifier")
    asset_job_id: UUID = Field(..., description="Associated job ID")
    asset_id: UUID | None = Field(None, description="Associated asset ID (once job succeeds)")
    source_id: UUID | None = Field(None, description="Related source ID")
    prompt_spec: dict = Field(..., description="Prompt spec used")
    input_hash: str = Field(..., description="Idempotency hash")
    lore_snapshot: LoreSnapshot | None = Field(None, description="Snapshot of lore inputs")
    created_at: datetime = Field(..., description="Creation timestamp")
    references: AssetJobReferences = Field(..., description="Lore references")


# ==================== Job Complete/Fail Request Models ====================


class AssetJobCompleteRequest(BaseModel):
    """Request body for completing a job with asset data."""

    asset: AssetCreate = Field(..., description="Asset data")


class AssetJobFailRequest(BaseModel):
    """Request body for marking a job as failed."""

    error_code: str = Field(..., max_length=100, description="Error code")
    error_message: str = Field(..., description="Error message")


# ==================== Job + Asset Response Models ====================


class AssetJobFullResponse(AssetJobResponse):
    """Full response for asset job including derivation and asset."""

    derivation: AssetDerivationResponse | None = Field(None, description="Provenance info")
    asset: AssetResponse | None = Field(None, description="Associated asset (if succeeded)")


# ==================== List/Filter Models ====================


class AssetListFilter(BaseModel):
    """Filters for listing assets."""

    world_id: UUID | None = Field(None, description="Filter by world")
    type: str | None = Field(None, description="Filter by asset type")
    status: str | None = Field(None, description="Filter by status")
    created_by: str | None = Field(None, description="Filter by creator")
    related_claim_id: UUID | None = Field(None, description="Filter by related claim")
    related_entity_id: UUID | None = Field(None, description="Filter by related entity")
    related_source_chunk_id: UUID | None = Field(None, description="Filter by related source chunk")
    source_id: UUID | None = Field(None, description="Filter by source")
    skip: int = Field(0, ge=0, description="Offset for pagination")
    limit: int = Field(10, ge=1, le=100, description="Limit for pagination")


class AssetJobListFilter(BaseModel):
    """Filters for listing asset jobs."""

    world_id: UUID | None = Field(None, description="Filter by world")
    status: str | None = Field(None, description="Filter by status")
    asset_type: str | None = Field(None, description="Filter by asset type")
    provider: str | None = Field(None, description="Filter by provider")
    requested_by: str | None = Field(None, description="Filter by requester")
    created_after: datetime | None = Field(None, description="Filter by creation date (after)")
    created_before: datetime | None = Field(None, description="Filter by creation date (before)")
    skip: int = Field(0, ge=0, description="Offset for pagination")
    limit: int = Field(10, ge=1, le=100, description="Limit for pagination")


# ==================== Paginated Response Models ====================


class PaginatedAssetResponse(BaseModel):
    """Paginated list of assets."""

    total: int = Field(..., description="Total count")
    skip: int = Field(..., description="Offset")
    limit: int = Field(..., description="Limit")
    items: list[AssetResponse] = Field(..., description="Asset items")


class PaginatedAssetJobResponse(BaseModel):
    """Paginated list of asset jobs."""

    total: int = Field(..., description="Total count")
    skip: int = Field(..., description="Offset")
    limit: int = Field(..., description="Limit")
    items: list[AssetJobFullResponse] = Field(..., description="Asset job items")
