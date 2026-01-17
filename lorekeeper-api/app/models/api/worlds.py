"""API models for world domain objects."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class WorldMetadata(BaseModel):
    """Metadata for a world."""

    themes: list[str] = Field(default_factory=list, description="World themes")
    era: str | None = Field(None, description="Global era")
    tags: list[str] = Field(default_factory=list, description="Custom tags")


class WorldBase(BaseModel):
    """Base World schema with common fields."""

    name: str = Field(..., max_length=255, description="World name")
    description: str | None = Field(None, description="World description")
    meta: WorldMetadata | None = Field(None, description="World metadata")


class WorldCreate(WorldBase):
    """Schema for creating a new world."""

    pass


class WorldUpdate(BaseModel):
    """Schema for updating a world."""

    name: str | None = Field(None, max_length=255, description="World name")
    description: str | None = Field(None, description="World description")
    meta: WorldMetadata | None = Field(None, description="World metadata")


class WorldResponse(WorldBase):
    """Schema for world responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="World unique identifier")
    created_at: datetime = Field(..., description="World creation timestamp")
    updated_at: datetime = Field(..., description="World last update timestamp")
