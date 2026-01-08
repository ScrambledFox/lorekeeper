"""
API routes for entity mention linking.

This module provides endpoints for managing mentions of entities within document snippets.
Supports both manual linking and automated string-match linking.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from lorekeeper.api.schemas import (
    AutoLinkRequest,
    EntityMentionCreate,
    EntityMentionResponse,
    SnippetWithMentions,
)
from lorekeeper.db.database import get_async_session
from lorekeeper.db.models import Document, DocumentSnippet, Entity, EntityMention, World

router = APIRouter(prefix="/worlds/{world_id}/snippets", tags=["entity-mentions"])


@router.post(
    "/{snippet_id}/mentions",
    response_model=EntityMentionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def link_entity_to_snippet(
    world_id: UUID,
    snippet_id: UUID,
    mention: EntityMentionCreate,
    session: AsyncSession = Depends(get_async_session),
) -> EntityMentionResponse:
    """
    Manually link an entity mention to a snippet.

    Args:
        world_id: World ID
        snippet_id: Snippet ID
        mention: Entity mention data
        session: Database session

    Returns:
        Created entity mention

    Raises:
        404: If world, snippet, or entity not found
        409: If mention already exists
    """
    # Verify world exists
    world = await session.get(World, world_id)
    if not world:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="World not found")

    # Verify snippet exists and belongs to world
    snippet = await session.get(DocumentSnippet, snippet_id)
    if not snippet or snippet.world_id != world_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Snippet not found")

    # Verify entity exists and belongs to world
    entity = await session.get(Entity, mention.entity_id)
    if not entity or entity.world_id != world_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entity not found")

    # Check if mention already exists
    existing = await session.scalar(
        select(EntityMention).where(
            and_(
                EntityMention.snippet_id == snippet_id,
                EntityMention.entity_id == mention.entity_id,
            )
        )
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Entity mention already exists for this snippet",
        )

    # Create mention
    entity_mention = EntityMention(
        snippet_id=snippet_id,
        entity_id=mention.entity_id,
        mention_text=mention.mention_text,
        confidence=mention.confidence,
    )
    session.add(entity_mention)
    await session.flush()
    await session.refresh(entity_mention)

    return EntityMentionResponse.model_validate(entity_mention)


@router.get("/{snippet_id}/mentions", response_model=list[EntityMentionResponse])
async def get_snippet_mentions(
    world_id: UUID,
    snippet_id: UUID,
    session: AsyncSession = Depends(get_async_session),
) -> list[EntityMentionResponse]:
    """
    Get all entity mentions for a snippet.

    Args:
        world_id: World ID
        snippet_id: Snippet ID
        session: Database session

    Returns:
        List of entity mentions

    Raises:
        404: If world or snippet not found
    """
    # Verify world exists
    world = await session.get(World, world_id)
    if not world:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="World not found")

    # Verify snippet exists and belongs to world
    snippet = await session.get(DocumentSnippet, snippet_id)
    if not snippet or snippet.world_id != world_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Snippet not found")

    # Get mentions
    mentions = await session.scalars(
        select(EntityMention)
        .where(EntityMention.snippet_id == snippet_id)
        .order_by(EntityMention.created_at)
    )

    return [EntityMentionResponse.model_validate(m) for m in mentions]


@router.get("/{snippet_id}", response_model=SnippetWithMentions)
async def get_snippet_with_mentions(
    world_id: UUID,
    snippet_id: UUID,
    session: AsyncSession = Depends(get_async_session),
) -> SnippetWithMentions:
    """
    Get a snippet with all its entity mentions.

    Args:
        world_id: World ID
        snippet_id: Snippet ID
        session: Database session

    Returns:
        Snippet with mentions

    Raises:
        404: If world or snippet not found
    """
    # Verify world exists
    world = await session.get(World, world_id)
    if not world:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="World not found")

    # Get snippet with document
    snippet = await session.get(DocumentSnippet, snippet_id)
    if not snippet or snippet.world_id != world_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Snippet not found")

    # Get associated document
    doc = await session.get(Document, snippet.document_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    # Get mentions
    mentions = await session.scalars(
        select(EntityMention)
        .where(EntityMention.snippet_id == snippet_id)
        .order_by(EntityMention.created_at)
    )

    # Determine reliability label
    reliability_label = f"{doc.mode}_SOURCE"

    return SnippetWithMentions(
        object_type="SNIPPET",
        snippet_id=snippet.id,
        document_id=snippet.document_id,
        world_id=snippet.world_id,
        snippet_text=snippet.snippet_text,
        start_char=snippet.start_char,
        end_char=snippet.end_char,
        document_title=doc.title,
        document_kind=doc.kind,
        document_mode=doc.mode,
        document_author=doc.author,
        in_world_date=doc.in_world_date,
        reliability_label=reliability_label,
        similarity_score=None,
        mentions=[EntityMentionResponse.model_validate(m) for m in mentions],
    )


@router.delete("/{snippet_id}/mentions/{mention_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mention(
    world_id: UUID,
    snippet_id: UUID,
    mention_id: UUID,
    session: AsyncSession = Depends(get_async_session),
) -> None:
    """
    Delete an entity mention.

    Args:
        world_id: World ID
        snippet_id: Snippet ID
        mention_id: Mention ID to delete
        session: Database session

    Raises:
        404: If world, snippet, or mention not found
    """
    # Verify world exists
    world = await session.get(World, world_id)
    if not world:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="World not found")

    # Verify snippet exists and belongs to world
    snippet = await session.get(DocumentSnippet, snippet_id)
    if not snippet or snippet.world_id != world_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Snippet not found")

    # Get and verify mention exists
    mention = await session.get(EntityMention, mention_id)
    if not mention or mention.snippet_id != snippet_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mention not found")

    await session.delete(mention)
    await session.flush()


@router.post("/{snippet_id}/auto-link", response_model=list[EntityMentionResponse])
async def auto_link_entities(
    world_id: UUID,
    snippet_id: UUID,
    request: AutoLinkRequest,
    session: AsyncSession = Depends(get_async_session),
) -> list[EntityMentionResponse]:
    """
    Automatically link entities to a snippet based on string matching.

    Searches for entity canonical names and aliases within the snippet text
    and creates mentions with confidence scores based on match quality.

    Args:
        world_id: World ID
        snippet_id: Snippet ID
        request: Auto-link configuration
        session: Database session

    Returns:
        List of created entity mentions

    Raises:
        404: If world or snippet not found
    """
    # Verify world exists
    world = await session.get(World, world_id)
    if not world:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="World not found")

    # Get snippet and verify it belongs to world
    snippet = await session.get(DocumentSnippet, snippet_id)
    if not snippet or snippet.world_id != world_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Snippet not found")

    # Get all entities in the world
    entities = await session.scalars(select(Entity).where(Entity.world_id == world_id))

    snippet_text_lower = snippet.snippet_text.lower()
    created_mentions: list[EntityMentionResponse] = []

    # Search for each entity in the snippet
    for entity in entities:
        # Check canonical name
        candidates = [(entity.canonical_name, 1.0)]

        # Add aliases with slightly lower confidence
        for alias in entity.aliases:
            candidates.append((alias, 0.95))

        for candidate_text, base_confidence in candidates:
            candidate_lower = candidate_text.lower()

            # Simple case-insensitive substring match
            if candidate_lower in snippet_text_lower:
                # Find actual occurrence in original text (preserve case)
                idx = snippet_text_lower.find(candidate_lower)
                actual_text = snippet.snippet_text[idx : idx + len(candidate_text)]

                # Check if mention already exists
                existing = await session.scalar(
                    select(EntityMention).where(
                        and_(
                            EntityMention.snippet_id == snippet_id,
                            EntityMention.entity_id == entity.id,
                        )
                    )
                )

                if existing:
                    if request.overwrite:
                        # Update existing mention
                        existing.confidence = base_confidence
                        existing.mention_text = actual_text
                        await session.flush()
                        await session.refresh(existing)
                        created_mentions.append(EntityMentionResponse.model_validate(existing))
                    continue

                # Only create if confidence meets threshold
                if base_confidence >= request.confidence_threshold:
                    mention = EntityMention(
                        snippet_id=snippet_id,
                        entity_id=entity.id,
                        mention_text=actual_text,
                        confidence=base_confidence,
                    )
                    session.add(mention)

        await session.flush()

    # Get all created mentions
    all_mentions = await session.scalars(
        select(EntityMention)
        .where(EntityMention.snippet_id == snippet_id)
        .order_by(EntityMention.created_at)
    )

    return [EntityMentionResponse.model_validate(m) for m in all_mentions]
