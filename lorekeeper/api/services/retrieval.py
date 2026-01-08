"""
Retrieval service for LoreKeeper - handles vector search and filtering logic.
"""

from typing import Optional
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from lorekeeper.api.schemas import (
    RetrievalEntityCard,
    RetrievalSnippetCard,
)
from lorekeeper.db.models import Document, DocumentSnippet, Entity


class RetrievalService:
    """Service for retrieving entities and snippets with various policies."""

    @staticmethod
    def _cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        # Convert to list if needed (pgvector returns numpy arrays)
        if hasattr(vec1, "tolist"):
            vec1 = vec1.tolist()
        if hasattr(vec2, "tolist"):
            vec2 = vec2.tolist()

        if not isinstance(vec1, list) or not isinstance(vec2, list):
            return 0.0
        if len(vec1) == 0 or len(vec2) == 0 or len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = sum(a * a for a in vec1) ** 0.5
        magnitude2 = sum(b * b for b in vec2) ** 0.5

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    @staticmethod
    async def retrieve_entities(
        session: AsyncSession,
        world_id: UUID,
        query: str,
        entity_types: Optional[list[str]] = None,
        tags: Optional[list[str]] = None,
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
            )
            for e in entities
        ]

    @staticmethod
    async def retrieve_snippets(
        session: AsyncSession,
        world_id: UUID,
        query_embedding: list[float],
        policy: str = "HYBRID",
        document_kinds: Optional[list[str]] = None,
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
                    similarity_score = RetrievalService._cosine_similarity(
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
                    reliability_label="CANON_SOURCE"
                    if document.mode == "STRICT"
                    else "MYTHIC_SOURCE",
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
        document_kinds: Optional[list[str]] = None,
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
