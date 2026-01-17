"""Claim API schemas."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


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
