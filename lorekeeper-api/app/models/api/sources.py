"""API models for source domain objects."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SourceBase(BaseModel):
    """Base Source schema with common fields."""

    world_id: UUID = Field(..., description="World identifier")
    type: str = Field(..., max_length=100, description="Source type")
    title: str = Field(..., max_length=255, description="Source title")
    author_ids: list[UUID] = Field(..., description="Author entity IDs")
    origin: str | None = Field(None, max_length=255, description="Origin or location")
    book_version_id: UUID | None = Field(None, description="Related book version ID")
    meta: dict | None = Field(None, description="Additional metadata")


class SourceCreate(SourceBase):
    """Schema for creating a new source."""

    pass


class SourceUpdate(BaseModel):
    """Schema for updating a source."""

    type: str | None = Field(None, max_length=100, description="Source type")
    title: str | None = Field(None, max_length=255, description="Source title")
    author_ids: list[str] | None = Field(None, description="Author entity IDs")
    origin: str | None = Field(None, max_length=255, description="Origin or location")
    book_version_id: str | None = Field(None, description="Related book version ID")
    meta: dict | None = Field(None, description="Additional metadata")


class SourceResponse(SourceBase):
    """Schema for source responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Source unique identifier")
    created_at: datetime = Field(..., description="Source creation timestamp")


class SourceChunkBase(BaseModel):
    """Base SourceChunk schema with common fields."""

    source_id: UUID = Field(..., description="Source identifier")
    chunk_index: int = Field(..., description="Chunk position in source")
    content: str = Field(..., description="Chunk text content")
    meta: dict | None = Field(None, description="Additional metadata")


class SourceChunkCreate(SourceChunkBase):
    """Schema for creating a new source chunk."""

    embedding: list[float] | None = Field(
        None,
        description="Vector embedding (optional; generated server-side if omitted)",
    )


class SourceChunkUpdate(BaseModel):
    """Schema for updating a source chunk."""

    content: str | None = Field(None, description="Chunk text content")
    embedding: list[float] | None = Field(None, description="Vector embedding")
    meta: dict | None = Field(None, description="Additional metadata")


class SourceChunkResponse(SourceChunkBase):
    """Schema for source chunk responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Source chunk unique identifier")
    created_at: datetime = Field(..., description="Source chunk creation timestamp")

    # Embedding field is typically excluded from responses unless specifically requested
    embedding: list[float] | None = Field(None, exclude=True, description="Vector embedding")
