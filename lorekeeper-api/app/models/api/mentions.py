"""Entity mention API schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


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
