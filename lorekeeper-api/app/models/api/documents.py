"""Document API schemas."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


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
