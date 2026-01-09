"""
Pydantic schemas for LoreKeeper API requests and responses.
"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# World Schemas
class WorldCreate(BaseModel):
    """Schema for creating a world."""

    name: str = Field(..., min_length=1, max_length=255, description="World name")
    description: str | None = Field(None, description="World description")


class WorldResponse(BaseModel):
    """Schema for world response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime


# Entity Schemas
class EntityCreate(BaseModel):
    """Schema for creating an entity."""

    type: str = Field(..., min_length=1, max_length=100, description="Entity type")
    canonical_name: str = Field(..., min_length=1, max_length=255)
    aliases: list[str] = Field(default_factory=list, description="Alternative names")
    summary: str | None = Field(None, max_length=500)
    description: str | None = Field(None, description="Full description")
    tags: list[str] = Field(default_factory=list, description="Tag list")
    is_fiction: bool = Field(False, description="Whether this entity is fiction (in-lore) or fact")


class EntityUpdate(BaseModel):
    """Schema for updating an entity."""

    canonical_name: str | None = None
    aliases: list[str] | None = None
    summary: str | None = None
    description: str | None = None
    tags: list[str] | None = None
    is_fiction: bool | None = None
    status: str | None = None


class EntityResponse(BaseModel):
    """Schema for entity response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    world_id: UUID
    type: str
    canonical_name: str
    aliases: list[str]
    summary: str | None
    description: str | None
    tags: list[str]
    is_fiction: bool
    status: str
    created_at: datetime
    updated_at: datetime


class EntitySearchResult(BaseModel):
    """Schema for entity search results."""

    total: int
    results: list[EntityResponse]


# Document Schemas
class DocumentCreate(BaseModel):
    """Schema for creating a document."""

    mode: str = Field(..., description="STRICT or MYTHIC")
    kind: str = Field(..., description="Document kind: CHRONICLE, SCRIPTURE, BALLAD, etc.")
    title: str = Field(..., min_length=1, max_length=255)
    author: str | None = Field(None, max_length=255)
    in_world_date: str | None = Field(None, max_length=255, description="In-world date string")
    text: str = Field(..., min_length=1, description="Full document text")
    provenance: dict[str, Any] | None = Field(None, description="Source metadata")


class DocumentResponse(BaseModel):
    """Schema for document response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    world_id: UUID
    mode: str
    kind: str
    title: str
    author: str | None
    in_world_date: str | None
    text: str
    provenance: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime


# Document Snippet Schemas
class DocumentSnippetCreate(BaseModel):
    """Schema for creating a document snippet."""

    document_id: UUID
    world_id: UUID
    snippet_index: int
    start_char: int
    end_char: int
    snippet_text: str
    embedding: list[float] | None = None


class DocumentSnippetResponse(BaseModel):
    """Schema for document snippet response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    world_id: UUID
    snippet_index: int
    start_char: int
    end_char: int
    snippet_text: str
    embedding: list[float] | None
    created_at: datetime


# Document Indexing Schemas
class DocumentIndexRequest(BaseModel):
    """Schema for document indexing request."""

    chunk_size_min: int = Field(300, ge=100, le=1000)
    chunk_size_max: int = Field(800, ge=100, le=2000)
    overlap_percentage: float = Field(0.15, ge=0.0, le=1.0)


class DocumentIndexResponse(BaseModel):
    """Schema for document indexing response."""

    document_id: UUID
    snippets_created: int
    snippet_ids: list[UUID]


# Search Schemas
class DocumentSearchRequest(BaseModel):
    """Schema for document search."""

    query: str | None = None
    mode: str | None = None  # STRICT, MYTHIC, or None for all
    kind: str | None = None
    limit: int = Field(10, ge=1, le=100)
    offset: int = Field(0, ge=0)


class DocumentSearchResult(BaseModel):
    """Schema for document search results."""

    total: int
    results: list[DocumentResponse]


# Retrieval Schemas
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


# Entity Mention Schemas
class EntityMentionCreate(BaseModel):
    """Schema for manually linking an entity to a snippet."""

    entity_id: UUID = Field(..., description="The entity being mentioned")
    mention_text: str = Field(..., min_length=1, max_length=255, description="Text of the mention")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Confidence score (0-1)")


class EntityMentionResponse(BaseModel):
    """Schema for entity mention response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    snippet_id: UUID
    entity_id: UUID
    mention_text: str
    confidence: float
    created_at: datetime


class SnippetWithMentions(BaseModel):
    """Extended snippet response that includes linked entity mentions."""

    model_config = ConfigDict(from_attributes=True)

    # All fields from RetrievalSnippetCard
    object_type: str = "SNIPPET"
    snippet_id: UUID
    document_id: UUID
    world_id: UUID
    snippet_text: str
    start_char: int
    end_char: int
    document_title: str
    document_kind: str
    document_mode: str
    document_author: str | None
    in_world_date: str | None
    reliability_label: str
    similarity_score: float | None = None

    # Entity mentions linked to this snippet
    mentions: list[EntityMentionResponse] = Field(default_factory=lambda: [])


class AutoLinkRequest(BaseModel):
    """Schema for automated entity mention linking request."""

    confidence_threshold: float = Field(
        0.7, ge=0.0, le=1.0, description="Minimum confidence for automated links"
    )
    overwrite: bool = Field(False, description="Overwrite existing mentions")


# Claim Schemas
class ClaimTruthEnum(str, Enum):
    """Truth value enum for claims."""

    CANON_TRUE = "CANON_TRUE"
    CANON_FALSE = "CANON_FALSE"


class ClaimCreate(BaseModel):
    """Schema for creating a claim."""

    subject_entity_id: UUID | None = Field(None, description="Subject entity ID")
    predicate: str = Field(..., min_length=1, max_length=255, description="Predicate")
    object_text: str | None = Field(None, description="Object text value")
    object_entity_id: UUID | None = Field(None, description="Object entity ID")
    truth_status: ClaimTruthEnum = Field(
        ClaimTruthEnum.CANON_TRUE, description="Truth status of the claim"
    )
    snippet_id: UUID | None = Field(None, description="Source snippet ID")
    belief_prevalence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="How widely believed is this claim (0.0=obscure, 1.0=universal)",
    )
    notes: str | None = Field(None, description="Optional notes about the claim")


class ClaimUpdate(BaseModel):
    """Schema for updating a claim."""

    truth_status: ClaimTruthEnum | None = Field(None, description="Update truth status")
    belief_prevalence: float | None = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Update how widely believed the claim is",
    )
    notes: str | None = Field(None, description="Update notes")


class ClaimResponse(BaseModel):
    """Schema for claim response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    world_id: UUID
    subject_entity_id: UUID | None
    predicate: str
    object_text: str | None
    object_entity_id: UUID | None
    truth_status: ClaimTruthEnum
    snippet_id: UUID | None
    belief_prevalence: float
    notes: str | None
    created_at: datetime
    updated_at: datetime


class SnippetAnalysisCreate(BaseModel):
    """Schema for creating snippet analysis."""

    snippet_id: UUID = Field(..., description="Snippet ID")
    world_id: UUID = Field(..., description="World ID")
    contradiction_score: float | None = Field(
        None, ge=0.0, le=1.0, description="Contradiction score (0-1)"
    )
    contains_claim_about_canon_entities: bool = Field(
        False, description="Whether snippet contains claims about canonical entities"
    )
    analysis_notes: str | None = Field(None, description="Analysis notes")
    analyzed_by: str = Field("manual", description="Analysis method")


class SnippetAnalysisResponse(BaseModel):
    """Schema for snippet analysis response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    world_id: UUID
    snippet_id: UUID
    contradiction_score: float | None
    contains_claim_about_canon_entities: bool
    analysis_notes: str | None
    analyzed_by: str
    created_at: datetime
    updated_at: datetime
