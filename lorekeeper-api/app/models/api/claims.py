"""API models for claim domain objects."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ClaimBase(BaseModel):
    """Base Claim schema with common fields."""

    world_id: UUID = Field(..., description="World identifier")
    subject_entity_id: UUID = Field(..., description="Subject entity identifier")
    predicate: str = Field(..., max_length=255, description="Claim predicate")
    object_entity_id: UUID | None = Field(None, description="Object entity identifier")
    object_value: dict | None = Field(None, description="Object value for non-entity objects")
    canon_state: str = Field(default="DRAFT", max_length=50, description="Canonical state")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="Confidence level")
    asserted_by_entity_id: UUID | None = Field(None, description="Entity making the assertion")
    source_id: UUID | None = Field(None, description="Source of the claim")
    created_by: str = Field(..., max_length=100, description="Creator identifier")
    version_group_id: UUID | None = Field(None, description="Version group identifier")
    supersedes_claim_id: UUID | None = Field(None, description="Superseded claim identifier")


class ClaimCreate(ClaimBase):
    """Schema for creating a new claim."""

    pass


class ClaimUpdate(BaseModel):
    """Schema for updating a claim."""

    predicate: str | None = Field(None, max_length=255, description="Claim predicate")
    object_entity_id: UUID | None = Field(None, description="Object entity identifier")
    object_value: dict | None = Field(None, description="Object value for non-entity objects")
    canon_state: str | None = Field(None, max_length=50, description="Canonical state")
    confidence: float | None = Field(None, ge=0.0, le=1.0, description="Confidence level")
    asserted_by_entity_id: UUID | None = Field(None, description="Entity making the assertion")
    source_id: UUID | None = Field(None, description="Source of the claim")
    supersedes_claim_id: UUID | None = Field(None, description="Superseded claim identifier")


class ClaimResponse(ClaimBase):
    """Schema for claim responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Claim unique identifier")
    created_at: datetime = Field(..., description="Claim creation timestamp")
    updated_at: datetime = Field(..., description="Claim last update timestamp")


class ClaimEmbeddingBase(BaseModel):
    """Base ClaimEmbedding schema with common fields."""

    claim_id: UUID = Field(..., description="Claim identifier")
    embedding: list[float] = Field(..., description="Vector embedding")
    model: str = Field(..., max_length=100, description="Embedding model")


class ClaimEmbeddingCreate(ClaimEmbeddingBase):
    """Schema for creating a new claim embedding."""

    pass


class ClaimEmbeddingUpdate(BaseModel):
    """Schema for updating a claim embedding."""

    embedding: list[float] | None = Field(None, description="Vector embedding")
    model: str | None = Field(None, max_length=100, description="Embedding model")


class ClaimEmbeddingResponse(ClaimEmbeddingBase):
    """Schema for claim embedding responses."""

    model_config = ConfigDict(from_attributes=True)

    created_at: datetime = Field(..., description="Claim embedding creation timestamp")


class ClaimTagBase(BaseModel):
    """Base ClaimTag schema with common fields."""

    claim_id: UUID = Field(..., description="Claim identifier")
    tag_id: UUID = Field(..., description="Tag identifier")


class ClaimTagCreate(ClaimTagBase):
    """Schema for creating a new claim tag association."""

    pass


class ClaimTagResponse(ClaimTagBase):
    """Schema for claim tag association responses."""

    model_config = ConfigDict(from_attributes=True)
