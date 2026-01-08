"""
Pydantic schemas for LoreKeeper API requests and responses.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


# World Schemas
class WorldCreate(BaseModel):
    """Schema for creating a world."""

    name: str = Field(..., min_length=1, max_length=255, description="World name")
    description: str | None = Field(None, description="World description")


class WorldResponse(BaseModel):
    """Schema for world response."""

    id: UUID
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Entity Schemas
class EntityCreate(BaseModel):
    """Schema for creating an entity."""

    type: str = Field(..., min_length=1, max_length=100, description="Entity type")
    canonical_name: str = Field(..., min_length=1, max_length=255)
    aliases: list[str] = Field(default_factory=list, description="Alternative names")
    summary: str | None = Field(None, max_length=500)
    description: str | None = Field(None, description="Full description")
    tags: list[str] = Field(default_factory=list, description="Tag list")


class EntityUpdate(BaseModel):
    """Schema for updating an entity."""

    canonical_name: str | None = None
    aliases: list[str] | None = None
    summary: str | None = None
    description: str | None = None
    tags: list[str] | None = None
    status: str | None = None


class EntityResponse(BaseModel):
    """Schema for entity response."""

    id: UUID
    world_id: UUID
    type: str
    canonical_name: str
    aliases: list[str]
    summary: str | None
    description: str | None
    tags: list[str]
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


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

    id: UUID
    document_id: UUID
    world_id: UUID
    snippet_index: int
    start_char: int
    end_char: int
    snippet_text: str
    embedding: list[float] | None
    created_at: datetime

    class Config:
        from_attributes = True


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
