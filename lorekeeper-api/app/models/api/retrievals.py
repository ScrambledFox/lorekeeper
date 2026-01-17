"""Retrieval API schemas."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RetrievalEntityCard(BaseModel):
    """Schema for entity card in retrieval results."""

    model_config = ConfigDict(from_attributes=True)

    object_type: str = "ENTITY"
    entity_id: UUID
    world_id: UUID
    type: str
    canonical_name: str
    aliases: list[str]
    summary: str | None
    description: str | None
    tags: list[str]
    is_fiction: bool
    reliability_label: str = "CANON"  # Always CANON for entities in Phase 1


class RetrievalSnippetCard(BaseModel):
    """Schema for snippet card in retrieval results."""

    model_config = ConfigDict(from_attributes=True)

    object_type: str = "SNIPPET"
    snippet_id: UUID
    document_id: UUID
    world_id: UUID
    snippet_text: str
    start_char: int
    end_char: int

    # Provenance fields
    document_title: str
    document_kind: str
    document_mode: str
    document_author: str | None
    in_world_date: str | None

    # Reliability and confidence
    reliability_label: str  # CANON_SOURCE or MYTHIC_SOURCE
    similarity_score: float | None = None  # Optional vector similarity score


class RetrievalRequest(BaseModel):
    """Schema for retrieval request."""

    query: str = Field(..., min_length=1, description="Search query")
    policy: str = Field("HYBRID", description="STRICT_ONLY, MYTHIC_ONLY, or HYBRID")
    top_k: int = Field(12, ge=1, le=100, description="Number of results to return")
    include_entities: bool = Field(True, description="Include entities in results")
    include_snippets: bool = Field(True, description="Include snippets in results")

    # Optional filters
    entity_types: list[str] | None = Field(None, description="Filter by entity types")
    document_kinds: list[str] | None = Field(None, description="Filter by document kinds")
    tags: list[str] | None = Field(None, description="Filter by tags")


class RetrievalResponse(BaseModel):
    """Schema for retrieval response."""

    query: str
    policy: str
    total_results: int

    entities: list[RetrievalEntityCard] = Field(default_factory=lambda: [])
    snippets: list[RetrievalSnippetCard] = Field(default_factory=lambda: [])

    # Optional debug information
    debug: dict[str, Any] | None = None
