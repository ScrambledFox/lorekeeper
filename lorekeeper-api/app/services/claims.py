"""Claim service for domain logic and embeddings."""

import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InternalServerErrorException
from app.models.api.claims import ClaimCreate
from app.models.db.claims import Claim, ClaimEmbedding
from app.repositories.claims import ClaimRepository
from app.services.embedding import EmbeddingService, EmbeddingServiceError
from app.services.embedding_factory import get_embedding_service
from app.types.embedding import EmbeddingOptions, EmbeddingPurpose


class ClaimService:
    """Service for claim creation and embedding persistence."""

    def __init__(
        self,
        embedding_service: EmbeddingService | None = None,
        repository: ClaimRepository | None = None,
    ) -> None:
        self._embedding_service = embedding_service or get_embedding_service()
        self._repository = repository or ClaimRepository()

    async def create_claims(self, session: AsyncSession, claims: list[ClaimCreate]) -> list[Claim]:
        """Create claims and persist embeddings."""
        try:
            db_claims = await self._repository.add_claims(session, claims)

            claim_texts = [self._canonical_claim_text(claim) for claim in db_claims]
            options = EmbeddingOptions(model="claims_v1", purpose=EmbeddingPurpose.CLAIM)
            try:
                embedding_results = self._embedding_service.embed_batch(claim_texts, options)
            except EmbeddingServiceError as exc:
                raise InternalServerErrorException(message=str(exc)) from exc

            if any(result.error or result.vector is None for result in embedding_results):
                error_messages = [
                    result.error.message for result in embedding_results if result.error is not None
                ]
                raise InternalServerErrorException(
                    message=f"Embedding failed for claims: {', '.join(error_messages)}"
                )

            claim_embeddings = [
                ClaimEmbedding(
                    claim_id=claim.id,
                    embedding=result.vector,
                    model=result.wrapper_model_alias,
                )
                for claim, result in zip(db_claims, embedding_results, strict=True)
            ]
            await self._repository.add_embeddings(session, claim_embeddings)
            await session.commit()
            return db_claims
        except Exception:
            await session.rollback()
            raise

    @staticmethod
    def _canonical_claim_text(claim: Claim) -> str:
        object_value = (
            json.dumps(claim.object_value, sort_keys=True, separators=(",", ":"))
            if claim.object_value
            else "null"
        )
        object_entity = str(claim.object_entity_id) if claim.object_entity_id else "null"
        asserted_by = str(claim.asserted_by_entity_id) if claim.asserted_by_entity_id else "null"
        source_id = str(claim.source_id) if claim.source_id else "null"
        return (
            f"[world={claim.world_id}] [subject={claim.subject_entity_id}] "
            f"[predicate={claim.predicate}] [object_entity={object_entity}] "
            f"[object_value={object_value}] [canon={claim.canon_state}] "
            f"[asserted_by={asserted_by}] [source={source_id}]"
        )


def get_claim_service() -> ClaimService:
    """FastAPI dependency provider for ClaimService."""
    return ClaimService()
