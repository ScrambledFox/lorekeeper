"""Asset domain models for multimodal asset storage and provenance."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.utils.datetime import utc_now


class AssetType:
    """Enumeration of asset types."""

    VIDEO = "VIDEO"
    AUDIO = "AUDIO"
    IMAGE = "IMAGE"
    MAP = "MAP"
    PDF = "PDF"


class AssetStatus:
    """Enumeration of asset statuses."""

    READY = "READY"
    FAILED = "FAILED"
    DELETED = "DELETED"


class Asset(Base):
    """Asset model representing produced artifacts stored in object storage (S3-compatible)."""

    __tablename__ = "asset"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    world_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    format: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default=AssetStatus.READY)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    duration_seconds: Mapped[int | None] = mapped_column(nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(nullable=True)
    checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)
    metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, nullable=False, index=True
    )

    # Relationships
    derivations: Mapped[list["AssetDerivation"]] = relationship(
        "AssetDerivation", back_populates="asset", foreign_keys="AssetDerivation.asset_id"
    )

    def __repr__(self) -> str:
        return f"<Asset id={self.id} type={self.type} world_id={self.world_id}>"


class AssetJobStatus:
    """Enumeration of asset job statuses."""

    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class AssetJob(Base):
    """AssetJob model tracking the asynchronous generation process."""

    __tablename__ = "asset_job"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    world_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    asset_type: Mapped[str] = mapped_column(String(50), nullable=False)
    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    model_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=AssetJobStatus.QUEUED, index=True
    )
    priority: Mapped[int | None] = mapped_column(nullable=True)
    requested_by: Mapped[str] = mapped_column(String(255), nullable=False)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    prompt_spec: Mapped[dict] = mapped_column(JSONB, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, nullable=False, index=True
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    derivations: Mapped[list["AssetDerivation"]] = relationship(
        "AssetDerivation", back_populates="job", foreign_keys="AssetDerivation.asset_job_id"
    )

    def __repr__(self) -> str:
        return f"<AssetJob id={self.id} status={self.status} asset_type={self.asset_type}>"


class AssetDerivation(Base):
    """AssetDerivation model linking jobs/assets to lore inputs (provenance)."""

    __tablename__ = "asset_derivation"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    world_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    asset_job_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("asset_job.id"), nullable=False, unique=True
    )
    asset_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("asset.id"), nullable=True
    )
    source_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    prompt_spec: Mapped[dict] = mapped_column(JSONB, nullable=False)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    lore_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    # Relationships
    job: Mapped["AssetJob"] = relationship(
        "AssetJob", back_populates="derivations", foreign_keys=[asset_job_id]
    )
    asset: Mapped["Asset | None"] = relationship(
        "Asset", back_populates="derivations", foreign_keys=[asset_id]
    )
    claims: Mapped[list["AssetDerivationClaim"]] = relationship(
        "AssetDerivationClaim", back_populates="derivation", cascade="all, delete-orphan"
    )
    entities: Mapped[list["AssetDerivationEntity"]] = relationship(
        "AssetDerivationEntity", back_populates="derivation", cascade="all, delete-orphan"
    )
    source_chunks: Mapped[list["AssetDerivationSourceChunk"]] = relationship(
        "AssetDerivationSourceChunk", back_populates="derivation", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<AssetDerivation id={self.id} job_id={self.asset_job_id}>"


class AssetDerivationClaim(Base):
    """Join table linking asset derivations to claims."""

    __tablename__ = "asset_derivation_claim"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    derivation_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("asset_derivation.id"), nullable=False, index=True
    )
    claim_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)

    # Relationships
    derivation: Mapped["AssetDerivation"] = relationship(
        "AssetDerivation", back_populates="claims", foreign_keys=[derivation_id]
    )

    def __repr__(self) -> str:
        return f"<AssetDerivationClaim derivation_id={self.derivation_id} claim_id={self.claim_id}>"


class AssetDerivationEntity(Base):
    """Join table linking asset derivations to entities."""

    __tablename__ = "asset_derivation_entity"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    derivation_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("asset_derivation.id"), nullable=False, index=True
    )
    entity_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)

    # Relationships
    derivation: Mapped["AssetDerivation"] = relationship(
        "AssetDerivation", back_populates="entities", foreign_keys=[derivation_id]
    )

    def __repr__(self) -> str:
        return (
            f"<AssetDerivationEntity derivation_id={self.derivation_id} entity_id={self.entity_id}>"
        )


class AssetDerivationSourceChunk(Base):
    """Join table linking asset derivations to source chunks."""

    __tablename__ = "asset_derivation_source_chunk"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    derivation_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("asset_derivation.id"), nullable=False, index=True
    )
    source_chunk_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)

    # Relationships
    derivation: Mapped["AssetDerivation"] = relationship(
        "AssetDerivation", back_populates="source_chunks", foreign_keys=[derivation_id]
    )

    def __repr__(self) -> str:
        return f"<AssetDerivationSourceChunk derivation_id={self.derivation_id} source_chunk_id={self.source_chunk_id}>"
