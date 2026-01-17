"""
Retrieval API routes for LoreKeeper.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_async_session
from app.indexer.chunker import EmbeddingService
from app.models.api.retrievals import RetrievalRequest, RetrievalResponse
from app.services.retrieval import RetrievalService

router = APIRouter(prefix="/worlds/{world_id}", tags=["retrieval"])

# Initialize services
embedding_service = EmbeddingService(model_name="mock")


@router.post("/retrieve", response_model=RetrievalResponse)
async def retrieve(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    world_id: UUID,
    request: RetrievalRequest,
) -> RetrievalResponse:
    """
    Retrieve entities and/or snippets from a world using semantic search.

    This is the primary retrieval endpoint that supports:
    - Vector similarity search across document snippets
    - Entity keyword search
    - Flexible retrieval policies (STRICT_ONLY, MYTHIC_ONLY, HYBRID)
    - Optional filtering by entity types, document kinds, and tags

    Args:
        world_id: World ID to search in
        request: Retrieval request with query and parameters
        session: Database session

    Returns:
        RetrievalResponse with entities and/or snippets based on policy and filters
    """
    try:
        # Validate policy
        if request.policy not in ("STRICT_ONLY", "MYTHIC_ONLY", "HYBRID"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid policy. Must be STRICT_ONLY, MYTHIC_ONLY, or HYBRID",
            )

        entities = []
        snippets = []

        # Generate embedding for the query
        query_embedding = embedding_service.embed(request.query)

        # Retrieve entities if requested
        if request.include_entities:
            entities = await RetrievalService.retrieve_entities(
                session=session,
                world_id=world_id,
                query=request.query,
                entity_types=request.entity_types,
                tags=request.tags,
                limit=request.top_k,
            )

        # Retrieve snippets if requested
        if request.include_snippets:
            snippets = await RetrievalService.retrieve_snippets(
                session=session,
                world_id=world_id,
                query_embedding=query_embedding,
                policy=request.policy,
                document_kinds=request.document_kinds,
                limit=request.top_k,
            )

        total_results = len(entities) + len(snippets)

        return RetrievalResponse(
            query=request.query,
            policy=request.policy,
            total_results=total_results,
            entities=entities,
            snippets=snippets,
            debug={
                "entities_count": len(entities),
                "snippets_count": len(snippets),
                "policy": request.policy,
                "include_entities": request.include_entities,
                "include_snippets": request.include_snippets,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Retrieval failed: {str(e)}",
        ) from e
