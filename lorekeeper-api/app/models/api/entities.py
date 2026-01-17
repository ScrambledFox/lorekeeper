"""API models for entity domain objects."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EntityBase(BaseModel):
    """Base Entity schema with common fields."""

    world_id: UUID = Field(..., description="World identifier")
    type: str = Field(..., max_length=100, description="Entity type")
    name: str = Field(..., max_length=255, description="Entity name")
    summary: str | None = Field(None, max_length=500, description="Brief summary")
    description: str | None = Field(None, description="Detailed description")
    meta: dict | None = Field(None, description="Additional metadata")


class EntityCreate(EntityBase):
    """Schema for creating a new entity."""

    pass


class EntityUpdate(BaseModel):
    """Schema for updating an entity."""

    type: str | None = Field(None, max_length=100, description="Entity type")
    name: str | None = Field(None, max_length=255, description="Entity name")
    summary: str | None = Field(None, max_length=500, description="Brief summary")
    description: str | None = Field(None, description="Detailed description")
    meta: dict | None = Field(None, description="Additional metadata")


class EntityResponse(EntityBase):
    """Schema for entity responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Entity unique identifier")
    created_at: datetime = Field(..., description="Entity creation timestamp")
    updated_at: datetime = Field(..., description="Entity last update timestamp")


class EntityAliasBase(BaseModel):
    """Base EntityAlias schema with common fields."""

    entity_id: UUID = Field(..., description="Entity identifier")
    alias: str = Field(..., max_length=255, description="Alias name")
    locale: str | None = Field(None, max_length=10, description="Locale code")
    source_note: str | None = Field(None, description="Source information")


class EntityAliasCreate(EntityAliasBase):
    """Schema for creating a new entity alias."""

    pass


class EntityAliasUpdate(BaseModel):
    """Schema for updating an entity alias."""

    alias: str | None = Field(None, max_length=255, description="Alias name")
    locale: str | None = Field(None, max_length=10, description="Locale code")
    source_note: str | None = Field(None, description="Source information")


class EntityAliasResponse(EntityAliasBase):
    """Schema for entity alias responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Entity alias unique identifier")
    created_at: datetime = Field(..., description="Entity alias creation timestamp")


class EntityTagBase(BaseModel):
    """Base EntityTag schema with common fields."""

    entity_id: UUID = Field(..., description="Entity identifier")
    tag_id: UUID = Field(..., description="Tag identifier")


class EntityTagCreate(EntityTagBase):
    """Schema for creating a new entity tag association."""

    pass


class EntityTagResponse(EntityTagBase):
    """Schema for entity tag association responses."""

    model_config = ConfigDict(from_attributes=True)
