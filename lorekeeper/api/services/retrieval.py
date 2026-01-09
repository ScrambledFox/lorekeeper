"""
Retrieval service for LoreKeeper - handles vector search and filtering logic.
"""

from collections.abc import Sequence
from enum import Enum
from typing import Protocol, runtime_checkable
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from lorekeeper.api.schemas import RetrievalEntityCard, RetrievalSnippetCard
from lorekeeper.db.models import Claim, ClaimTruth, Document, DocumentSnippet, Entity


class RetrievalPolicy(str, Enum):
    """Retrieval policy for filtering snippets and claims by truth status and belief prevalence."""

    STRICT_ONLY = "STRICT_ONLY"
    MYTHIC_ONLY = "MYTHIC_ONLY"
    HYBRID = "HYBRID"
    # Truth-based policies
    CANON_TRUE_ONLY = "CANON_TRUE_ONLY"  # Only canonically verified facts
    CANON_FALSE_ONLY = "CANON_FALSE_ONLY"  # Only known false claims (myths)
    # Belief-based policies
    WIDELY_BELIEVED = "WIDELY_BELIEVED"  # Claims widely believed (prevalence >= 0.7)
    OBSCURE = "OBSCURE"  # Claims that are obscure/unknown (prevalence < 0.5)


@runtime_checkable
class _HasToList(Protocol):
    """Protocol for objects that expose a list-like view."""

    def tolist(self) -> list[float]: ...


class RetrievalService:
    """Service for retrieving entities and snippets with various policies."""

    @staticmethod
    def cosine_similarity(
        vec1: Sequence[float] | _HasToList, vec2: Sequence[float] | _HasToList
    ) -> float:
        """Calculate cosine similarity between two vectors."""
        vec1_list = vec1.tolist() if isinstance(vec1, _HasToList) else list(vec1)
        vec2_list = vec2.tolist() if isinstance(vec2, _HasToList) else list(vec2)

        if len(vec1_list) == 0 or len(vec2_list) == 0 or len(vec1_list) != len(vec2_list):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1_list, vec2_list, strict=True))
        magnitude1 = sum(a * a for a in vec1_list) ** 0.5
        magnitude2 = sum(b * b for b in vec2_list) ** 0.5

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return float(dot_product / (magnitude1 * magnitude2))

    # Backward-compatible alias
    _cosine_similarity = cosine_similarity

    @staticmethod
    async def retrieve_entities(
        session: AsyncSession,
        world_id: UUID,
        query: str,
        entity_types: list[str] | None = None,
        tags: list[str] | None = None,
        limit: int = 10,
    ) -> list[RetrievalEntityCard]:
        """
        Retrieve entities matching the query.

        Args:
            session: Database session
            world_id: World ID to search in
            query: Search query
            entity_types: Optional filter by entity types
            tags: Optional filter by tags
            limit: Maximum number of results

        Returns:
            List of RetrievalEntityCard objects
        """
        search_term = f"%{query}%"

        # Build query
        q = select(Entity).where(
            and_(
                Entity.world_id == world_id,
                Entity.canonical_name.ilike(search_term),
            )
        )

        if entity_types:
            q = q.where(Entity.type.in_(entity_types))

        q = q.limit(limit)

        result = await session.execute(q)
        entities = result.scalars().all()

        return [
            RetrievalEntityCard(
                entity_id=e.id,
                world_id=e.world_id,
                type=e.type,
                canonical_name=e.canonical_name,
                aliases=e.aliases,
                summary=e.summary,
                description=e.description,
                tags=e.tags,
                is_fiction=e.is_fiction,
            )
            for e in entities
        ]

    @staticmethod
    async def retrieve_snippets(
        session: AsyncSession,
        world_id: UUID,
        query_embedding: list[float] | None,
        policy: str = "HYBRID",
        document_kinds: list[str] | None = None,
        limit: int = 10,
    ) -> list[RetrievalSnippetCard]:
        """
        Retrieve document snippets using vector similarity search.

        Args:
            session: Database session
            world_id: World ID to search in
            query_embedding: Embedding vector for the query
            policy: Retrieval policy (STRICT_ONLY, MYTHIC_ONLY, HYBRID)
            document_kinds: Optional filter by document kinds
            limit: Maximum number of results

        Returns:
            List of RetrievalSnippetCard objects sorted by similarity
        """
        try:
            # Build query
            q = select(DocumentSnippet, Document).where(
                and_(
                    DocumentSnippet.world_id == world_id,
                    DocumentSnippet.document_id == Document.id,
                )
            )

            # Apply policy filter
            if policy == "STRICT_ONLY":
                q = q.where(Document.mode == "STRICT")
            elif policy == "MYTHIC_ONLY":
                q = q.where(Document.mode == "MYTHIC")
            # HYBRID: no filter, include both

            if document_kinds and len(document_kinds) > 0:
                q = q.where(Document.kind.in_(document_kinds))

            result = await session.execute(q)
            snippet_pairs = result.all()

            # Calculate similarity scores and create cards
            cards_with_scores: list[tuple[RetrievalSnippetCard, float]] = []

            for snippet, document in snippet_pairs:
                # Calculate similarity if embeddings exist
                similarity_score = None
                if (
                    snippet.embedding is not None
                    and len(snippet.embedding) > 0
                    and query_embedding is not None
                    and len(query_embedding) > 0
                ):
                    similarity_score = RetrievalService.cosine_similarity(
                        snippet.embedding, query_embedding
                    )

                card = RetrievalSnippetCard(
                    snippet_id=snippet.id,
                    document_id=document.id,
                    world_id=snippet.world_id,
                    snippet_text=snippet.snippet_text,
                    start_char=snippet.start_char,
                    end_char=snippet.end_char,
                    document_title=document.title,
                    document_kind=document.kind,
                    document_mode=document.mode,
                    document_author=document.author,
                    in_world_date=document.in_world_date,
                    reliability_label=(
                        "CANON_SOURCE" if document.mode == "STRICT" else "MYTHIC_SOURCE"
                    ),
                    similarity_score=similarity_score,
                )
                cards_with_scores.append((card, similarity_score or 0.0))

            # Sort by similarity score (highest first), but put STRICT before MYTHIC if same score
            # When using HYBRID policy, STRICT sources are ranked higher
            cards_with_scores.sort(
                key=lambda x: (
                    0 if x[0].reliability_label == "CANON_SOURCE" else 1,  # STRICT/CANON first
                    -x[1],  # Then higher similarity
                )
            )

            return [card for card, _ in cards_with_scores[:limit]]
        except Exception as e:
            import traceback

            print(f"Error in retrieve_snippets: {e}")
            traceback.print_exc()
            raise

    @staticmethod
    async def retrieve_by_text_search(
        session: AsyncSession,
        world_id: UUID,
        query: str,
        policy: str = "HYBRID",
        document_kinds: list[str] | None = None,
        limit: int = 10,
    ) -> list[RetrievalSnippetCard]:
        """
        Retrieve snippets using text search (keyword matching).
        Used when query_embedding is not available or for semantic search fallback.

        Args:
            session: Database session
            world_id: World ID to search in
            query: Search query string
            policy: Retrieval policy
            document_kinds: Optional filter by document kinds
            limit: Maximum number of results

        Returns:
            List of RetrievalSnippetCard objects
        """
        search_term = f"%{query}%"

        q = select(DocumentSnippet, Document).where(
            and_(
                DocumentSnippet.world_id == world_id,
                DocumentSnippet.document_id == Document.id,
                DocumentSnippet.snippet_text.ilike(search_term),
            )
        )

        # Apply policy filter
        if policy == "STRICT_ONLY":
            q = q.where(Document.mode == "STRICT")
        elif policy == "MYTHIC_ONLY":
            q = q.where(Document.mode == "MYTHIC")

        if document_kinds:
            q = q.where(Document.kind.in_(document_kinds))

        q = q.limit(limit)

        result = await session.execute(q)
        snippet_pairs = result.all()

        cards = [
            RetrievalSnippetCard(
                snippet_id=snippet.id,
                document_id=document.id,
                world_id=snippet.world_id,
                snippet_text=snippet.snippet_text,
                start_char=snippet.start_char,
                end_char=snippet.end_char,
                document_title=document.title,
                document_kind=document.kind,
                document_mode=document.mode,
                document_author=document.author,
                in_world_date=document.in_world_date,
                reliability_label="CANON_SOURCE" if document.mode == "STRICT" else "MYTHIC_SOURCE",
                similarity_score=None,
            )
            for snippet, document in snippet_pairs
        ]

        return cards

    @staticmethod
    async def retrieve_snippets_by_truth_status(  # noqa: C901
        session: AsyncSession,
        world_id: UUID,
        query_embedding: list[float] | None,
        policy: str = "HYBRID",
        truth_policy: str = "HYBRID",
        document_kinds: list[str] | None = None,
        limit: int = 10,
    ) -> list[RetrievalSnippetCard]:
        """
        Retrieve snippets with optional truth status filtering based on associated claims.

        Args:
            session: Database session
            world_id: World ID to search in
            query_embedding: Embedding vector for the query
            policy: Document retrieval policy (STRICT_ONLY, MYTHIC_ONLY, HYBRID)
            truth_policy: Truth status policy (CANON_TRUE_ONLY, NO_CANON_FALSE, IN_WORLD_BELIEFS, HYBRID)
            document_kinds: Optional filter by document kinds
            limit: Maximum number of results

        Returns:
            List of RetrievalSnippetCard objects sorted by similarity
        """
        try:
            # Start with base query
            q = select(DocumentSnippet, Document).where(
                and_(
                    DocumentSnippet.world_id == world_id,
                    DocumentSnippet.document_id == Document.id,
                )
            )

            # Apply document policy filter (STRICT/MYTHIC)
            if policy == "STRICT_ONLY":
                q = q.where(Document.mode == "STRICT")
            elif policy == "MYTHIC_ONLY":
                q = q.where(Document.mode == "MYTHIC")

            if document_kinds and len(document_kinds) > 0:
                q = q.where(Document.kind.in_(document_kinds))

            result = await session.execute(q)
            snippet_pairs: list[tuple[DocumentSnippet, Document]] = [
                tuple(row) for row in result.all()
            ]

            # Filter by truth status if using claim-based policies
            filtered_snippets: list[tuple[DocumentSnippet, Document]] = []

            if truth_policy == "CANON_TRUE_ONLY":
                # Only include snippets with CANON_TRUE claims
                for snippet, document in snippet_pairs:
                    # Check if snippet has any CANON_TRUE claims
                    claim_query = select(Claim).where(
                        and_(
                            Claim.snippet_id == snippet.id,
                            Claim.truth_status == ClaimTruth.CANON_TRUE,
                        )
                    )
                    claim_result = await session.execute(claim_query)
                    if claim_result.scalars().first():
                        filtered_snippets.append((snippet, document))

            elif truth_policy == "NO_CANON_FALSE":
                # Exclude snippets with CANON_FALSE claims
                for snippet, document in snippet_pairs:
                    # Check if snippet has any CANON_FALSE claims
                    claim_query = select(Claim).where(
                        and_(
                            Claim.snippet_id == snippet.id,
                            Claim.truth_status == ClaimTruth.CANON_FALSE,
                        )
                    )
                    claim_result = await session.execute(claim_query)
                    if not claim_result.scalars().first():
                        filtered_snippets.append((snippet, document))

            elif truth_policy == "IN_WORLD_BELIEFS":
                # Include snippets with CANON_TRUE claims
                for snippet, document in snippet_pairs:
                    # Check if snippet has any CANON_TRUE claims
                    claim_query = select(Claim).where(
                        and_(
                            Claim.snippet_id == snippet.id,
                            Claim.truth_status.in_([ClaimTruth.CANON_TRUE]),
                        )
                    )
                    claim_result = await session.execute(claim_query)
                    if claim_result.scalars().first():
                        filtered_snippets.append((snippet, document))

            else:
                # HYBRID: no truth status filtering
                filtered_snippets = snippet_pairs

            # Calculate similarity scores and create cards
            cards_with_scores: list[tuple[RetrievalSnippetCard, float]] = []

            for snippet, document in filtered_snippets:
                # Calculate similarity if embeddings exist
                similarity_score = None
                if (
                    snippet.embedding is not None
                    and len(snippet.embedding) > 0
                    and query_embedding is not None
                    and len(query_embedding) > 0
                ):
                    similarity_score = RetrievalService.cosine_similarity(
                        snippet.embedding, query_embedding
                    )

                card = RetrievalSnippetCard(
                    snippet_id=snippet.id,
                    document_id=document.id,
                    world_id=snippet.world_id,
                    snippet_text=snippet.snippet_text,
                    start_char=snippet.start_char,
                    end_char=snippet.end_char,
                    document_title=document.title,
                    document_kind=document.kind,
                    document_mode=document.mode,
                    document_author=document.author,
                    in_world_date=document.in_world_date,
                    reliability_label=(
                        "CANON_SOURCE" if document.mode == "STRICT" else "MYTHIC_SOURCE"
                    ),
                    similarity_score=similarity_score,
                )
                cards_with_scores.append((card, similarity_score or 0.0))

            # Sort by similarity score (highest first), STRICT before MYTHIC if same score
            cards_with_scores.sort(
                key=lambda x: (
                    0 if x[0].reliability_label == "CANON_SOURCE" else 1,
                    -x[1],
                )
            )

            return [card for card, _ in cards_with_scores[:limit]]

        except Exception as e:
            import traceback

            print(f"Error in retrieve_snippets_by_truth_status: {e}")
            traceback.print_exc()
            raise
