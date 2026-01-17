"""API models for common domain objects."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TagBase(BaseModel):
    """Base Tag schema with common fields."""

    name: str = Field(..., max_length=100, description="Tag name")
    description: str | None = Field(None, description="Tag description")
    kind: str | None = Field(None, max_length=50, description="Tag category or type")


class TagCreate(TagBase):
    """Schema for creating a new tag."""

    pass


class TagUpdate(BaseModel):
    """Schema for updating a tag."""

    name: str | None = Field(None, max_length=100, description="Tag name")
    description: str | None = Field(None, description="Tag description")
    kind: str | None = Field(None, max_length=50, description="Tag category or type")


class TagResponse(TagBase):
    """Schema for tag responses."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Tag unique identifier")
    created_at: datetime = Field(..., description="Tag creation timestamp")
