"""Claim repository for data access."""

from sqlalchemy import String, cast, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api.claims import ClaimCreate
from app.models.db.claims import Claim, ClaimEmbedding


class ClaimRepository:
    """Repository for claim persistence and queries."""

    async def add_claims(self, session: AsyncSession, claims: list[ClaimCreate]) -> list[Claim]:
        db_claims = [
            Claim(
                world_id=claim.world_id,
                subject_entity_id=claim.subject_entity_id,
                predicate=claim.predicate,
                object_entity_id=claim.object_entity_id,
                object_value=claim.object_value,
                canon_state=claim.canon_state,
                confidence=claim.confidence,
                asserted_by_entity_id=claim.asserted_by_entity_id,
                source_id=claim.source_id,
                created_by=claim.created_by,
                version_group_id=claim.version_group_id,
                supersedes_claim_id=claim.supersedes_claim_id,
            )
            for claim in claims
        ]
        session.add_all(db_claims)
        await session.flush()
        return db_claims

    async def add_embeddings(self, session: AsyncSession, embeddings: list[ClaimEmbedding]) -> None:
        session.add_all(embeddings)

    async def list_claims(
        self,
        session: AsyncSession,
        skip: int,
        limit: int,
        world_id: str | None,
        entity_id: str | None,
        canon_state: str | None,
        predicate: str | None,
    ) -> list[Claim]:
        query = select(Claim)

        if world_id:
            query = query.where(Claim.world_id == world_id)
        if entity_id:
            query = query.where(
                (Claim.subject_entity_id == entity_id) | (Claim.object_entity_id == entity_id)
            )
        if canon_state:
            query = query.where(Claim.canon_state == canon_state)
        if predicate:
            query = query.where(Claim.predicate.ilike(f"%{predicate}%"))

        result = await session.execute(query.offset(skip).limit(limit))
        return list(result.scalars().all())

    async def get_claim(self, session: AsyncSession, claim_id: str) -> Claim | None:
        result = await session.execute(select(Claim).where(Claim.id == claim_id))
        return result.scalars().first()

    async def search_claims(
        self, session: AsyncSession, query_text: str, skip: int, limit: int
    ) -> list[Claim]:
        search = f"%{query_text}%"
        query = (
            select(Claim)
            .where(Claim.predicate.ilike(search) | cast(Claim.object_value, String).ilike(search))
            .offset(skip)
            .limit(limit)
        )
        result = await session.execute(query)
        return list(result.scalars().all())
