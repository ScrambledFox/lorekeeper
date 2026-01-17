"""Asset repository for data access."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import and_, select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.api.assets import (
    AssetCreate,
    AssetJobCreate,
    AssetJobUpdate,
    AssetJobStatusEnum,
)
from app.models.db.assets import (
    Asset,
    AssetJob,
    AssetDerivation,
    AssetDerivationClaim,
    AssetDerivationEntity,
    AssetDerivationSourceChunk,
    AssetStatus,
    AssetJobStatus,
)


class AssetRepository:
    """Repository for asset persistence and queries."""

    # ==================== Asset Operations ====================

    async def create_asset(self, session: AsyncSession, asset: AssetCreate) -> Asset:
        """Create a new asset."""
        db_asset = Asset(
            world_id=asset.world_id,
            type=asset.type,
            format=asset.format,
            status=AssetStatus.READY,
            storage_key=asset.storage_key,
            content_type=asset.content_type,
            duration_seconds=asset.duration_seconds,
            size_bytes=asset.size_bytes,
            checksum=asset.checksum,
            metadata=asset.metadata.model_dump() if asset.metadata else None,
            created_by=asset.created_by,
        )
        session.add(db_asset)
        await session.flush()
        return db_asset

    async def get_asset(self, session: AsyncSession, asset_id: UUID) -> Asset | None:
        """Get an asset by ID."""
        result = await session.execute(
            select(Asset).where(Asset.id == asset_id).options(joinedload(Asset.derivations))
        )
        return result.unique().scalars().first()

    async def list_assets(
        self,
        session: AsyncSession,
        world_id: UUID | None = None,
        asset_type: str | None = None,
        status: str | None = None,
        created_by: str | None = None,
        related_claim_id: UUID | None = None,
        related_entity_id: UUID | None = None,
        related_source_chunk_id: UUID | None = None,
        source_id: UUID | None = None,
        skip: int = 0,
        limit: int = 10,
    ) -> tuple[list[Asset], int]:
        """List assets with optional filtering."""
        query = select(Asset)

        if world_id:
            query = query.where(Asset.world_id == world_id)
        if asset_type:
            query = query.where(Asset.type == asset_type)
        if status:
            query = query.where(Asset.status == status)
        if created_by:
            query = query.where(Asset.created_by == created_by)

        # Handle related lore references via joins
        if related_claim_id:
            query = (
                query.join(AssetDerivation, Asset.id == AssetDerivation.asset_id)
                .join(
                    AssetDerivationClaim, AssetDerivation.id == AssetDerivationClaim.derivation_id
                )
                .where(AssetDerivationClaim.claim_id == related_claim_id)
            )
        elif related_entity_id:
            query = (
                query.join(AssetDerivation, Asset.id == AssetDerivation.asset_id)
                .join(
                    AssetDerivationEntity, AssetDerivation.id == AssetDerivationEntity.derivation_id
                )
                .where(AssetDerivationEntity.entity_id == related_entity_id)
            )
        elif related_source_chunk_id:
            query = (
                query.join(AssetDerivation, Asset.id == AssetDerivation.asset_id)
                .join(
                    AssetDerivationSourceChunk,
                    AssetDerivation.id == AssetDerivationSourceChunk.derivation_id,
                )
                .where(AssetDerivationSourceChunk.source_chunk_id == related_source_chunk_id)
            )
        elif source_id:
            query = query.join(AssetDerivation, Asset.id == AssetDerivation.asset_id).where(
                AssetDerivation.source_id == source_id
            )

        # Get total count
        count_result = await session.execute(select(func.count()).select_from(query.subquery()))
        total = count_result.scalar() or 0

        # Apply pagination and ordering
        query = query.order_by(Asset.created_at.desc()).offset(skip).limit(limit)
        result = await session.execute(query)
        assets = result.unique().scalars().all()

        return assets, total

    # ==================== AssetJob Operations ====================

    async def create_asset_job(
        self, session: AsyncSession, job: AssetJobCreate, requested_by: str, input_hash: str
    ) -> AssetJob:
        """Create a new asset job."""
        db_job = AssetJob(
            world_id=job.world_id,
            asset_type=job.asset_type,
            provider=job.provider,
            model_id=job.model_id,
            status=AssetJobStatus.QUEUED,
            priority=job.priority,
            requested_by=requested_by,
            input_hash=input_hash,
            prompt_spec=job.prompt_spec
            if isinstance(job.prompt_spec, dict)
            else job.prompt_spec.model_dump(),
        )
        session.add(db_job)
        await session.flush()
        return db_job

    async def get_asset_job(self, session: AsyncSession, job_id: UUID) -> AssetJob | None:
        """Get an asset job by ID."""
        result = await session.execute(
            select(AssetJob)
            .where(AssetJob.id == job_id)
            .options(
                joinedload(AssetJob.derivations).joinedload(AssetDerivation.claims),
                joinedload(AssetJob.derivations).joinedload(AssetDerivation.entities),
                joinedload(AssetJob.derivations).joinedload(AssetDerivation.source_chunks),
                joinedload(AssetJob.derivations).joinedload(AssetDerivation.asset),
            )
        )
        return result.unique().scalars().first()

    async def get_asset_job_by_input_hash(
        self, session: AsyncSession, world_id: UUID, input_hash: str
    ) -> AssetJob | None:
        """Get the most recent asset job by world and input hash."""
        result = await session.execute(
            select(AssetJob)
            .where(
                and_(
                    AssetJob.world_id == world_id,
                    AssetJob.input_hash == input_hash,
                )
            )
            .order_by(AssetJob.created_at.desc())
            .limit(1)
            .options(
                joinedload(AssetJob.derivations).joinedload(AssetDerivation.claims),
                joinedload(AssetJob.derivations).joinedload(AssetDerivation.entities),
                joinedload(AssetJob.derivations).joinedload(AssetDerivation.source_chunks),
                joinedload(AssetJob.derivations).joinedload(AssetDerivation.asset),
            )
        )
        return result.unique().scalars().first()

    async def update_asset_job_status(
        self,
        session: AsyncSession,
        job_id: UUID,
        status: str,
        started_at=None,
        finished_at=None,
        error_code=None,
        error_message=None,
    ) -> AssetJob | None:
        """Update an asset job's status and related fields."""
        result = await session.execute(select(AssetJob).where(AssetJob.id == job_id))
        job = result.scalars().first()

        if not job:
            return None

        job.status = status
        if started_at:
            job.started_at = started_at
        if finished_at:
            job.finished_at = finished_at
        if error_code:
            job.error_code = error_code
        if error_message:
            job.error_message = error_message

        await session.flush()
        return job

    async def list_asset_jobs(
        self,
        session: AsyncSession,
        world_id: UUID | None = None,
        status: str | None = None,
        asset_type: str | None = None,
        provider: str | None = None,
        requested_by: str | None = None,
        created_after=None,
        created_before=None,
        skip: int = 0,
        limit: int = 10,
    ) -> tuple[list[AssetJob], int]:
        """List asset jobs with optional filtering."""
        query = select(AssetJob)

        if world_id:
            query = query.where(AssetJob.world_id == world_id)
        if status:
            query = query.where(AssetJob.status == status)
        if asset_type:
            query = query.where(AssetJob.asset_type == asset_type)
        if provider:
            query = query.where(AssetJob.provider == provider)
        if requested_by:
            query = query.where(AssetJob.requested_by == requested_by)
        if created_after:
            query = query.where(AssetJob.created_at >= created_after)
        if created_before:
            query = query.where(AssetJob.created_at <= created_before)

        # Get total count
        count_result = await session.execute(select(func.count()).select_from(query.subquery()))
        total = count_result.scalar() or 0

        # Apply pagination and ordering
        query = (
            query.order_by(AssetJob.created_at.desc())
            .offset(skip)
            .limit(limit)
            .options(
                joinedload(AssetJob.derivations).joinedload(AssetDerivation.claims),
                joinedload(AssetJob.derivations).joinedload(AssetDerivation.entities),
                joinedload(AssetJob.derivations).joinedload(AssetDerivation.source_chunks),
                joinedload(AssetJob.derivations).joinedload(AssetDerivation.asset),
            )
        )
        result = await session.execute(query)
        jobs = result.unique().scalars().all()

        return jobs, total

    # ==================== AssetDerivation Operations ====================

    async def create_asset_derivation(
        self,
        session: AsyncSession,
        asset_job_id: UUID,
        world_id: UUID,
        prompt_spec: dict,
        input_hash: str,
        lore_snapshot: dict | None = None,
        source_id: UUID | None = None,
    ) -> AssetDerivation:
        """Create a new asset derivation."""
        db_derivation = AssetDerivation(
            asset_job_id=asset_job_id,
            world_id=world_id,
            prompt_spec=prompt_spec,
            input_hash=input_hash,
            lore_snapshot=lore_snapshot,
            source_id=source_id,
        )
        session.add(db_derivation)
        await session.flush()
        return db_derivation

    async def get_asset_derivation(
        self, session: AsyncSession, derivation_id: UUID
    ) -> AssetDerivation | None:
        """Get an asset derivation by ID."""
        result = await session.execute(
            select(AssetDerivation)
            .where(AssetDerivation.id == derivation_id)
            .options(
                joinedload(AssetDerivation.claims),
                joinedload(AssetDerivation.entities),
                joinedload(AssetDerivation.source_chunks),
            )
        )
        return result.scalars().first()

    async def get_derivation_by_job_id(
        self, session: AsyncSession, asset_job_id: UUID
    ) -> AssetDerivation | None:
        """Get the derivation for a specific job."""
        result = await session.execute(
            select(AssetDerivation)
            .where(AssetDerivation.asset_job_id == asset_job_id)
            .options(
                joinedload(AssetDerivation.claims),
                joinedload(AssetDerivation.entities),
                joinedload(AssetDerivation.source_chunks),
                joinedload(AssetDerivation.asset),
            )
        )
        return result.unique().scalars().first()

    async def add_derivation_claims(
        self, session: AsyncSession, derivation_id: UUID, claim_ids: list[UUID]
    ) -> list[AssetDerivationClaim]:
        """Add claim references to a derivation."""
        claims = [
            AssetDerivationClaim(derivation_id=derivation_id, claim_id=cid) for cid in claim_ids
        ]
        session.add_all(claims)
        await session.flush()
        return claims

    async def add_derivation_entities(
        self, session: AsyncSession, derivation_id: UUID, entity_ids: list[UUID]
    ) -> list[AssetDerivationEntity]:
        """Add entity references to a derivation."""
        entities = [
            AssetDerivationEntity(derivation_id=derivation_id, entity_id=eid) for eid in entity_ids
        ]
        session.add_all(entities)
        await session.flush()
        return entities

    async def add_derivation_source_chunks(
        self, session: AsyncSession, derivation_id: UUID, source_chunk_ids: list[UUID]
    ) -> list[AssetDerivationSourceChunk]:
        """Add source chunk references to a derivation."""
        chunks = [
            AssetDerivationSourceChunk(derivation_id=derivation_id, source_chunk_id=scid)
            for scid in source_chunk_ids
        ]
        session.add_all(chunks)
        await session.flush()
        return chunks

    async def update_derivation_asset_id(
        self, session: AsyncSession, derivation_id: UUID, asset_id: UUID
    ) -> AssetDerivation | None:
        """Update a derivation's asset_id (called when job succeeds)."""
        result = await session.execute(
            select(AssetDerivation).where(AssetDerivation.id == derivation_id)
        )
        derivation = result.scalars().first()

        if not derivation:
            return None

        derivation.asset_id = asset_id
        await session.flush()
        return derivation
