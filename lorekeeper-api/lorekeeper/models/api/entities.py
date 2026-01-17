"""Entity API schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


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
