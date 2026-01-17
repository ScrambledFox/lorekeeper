"""API models for book domain objects."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BookBase(BaseModel):
    """Base Book schema with common fields."""

    world_id: UUID = Field(..., description="World identifier")
    title: str = Field(..., max_length=255, description="Book title")
    writer_ids: list[UUID | None] | None = Field(None, description="Writer entity IDs")
    meta: dict | None = Field(None, description="Additional metadata")


class BookCreate(BookBase):
    """Schema for creating a new book."""

    pass


class BookUpdate(BaseModel):
    """Schema for updating a book."""

    title: str | None = Field(None, max_length=255, description="Book title")
    writer_ids: list[UUID | None] | None = Field(None, description="Writer entity IDs")
    meta: dict | None = Field(None, description="Additional metadata")


class BookResponse(BookBase):
    """Schema for book responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Book unique identifier")
    created_at: datetime = Field(..., description="Book creation timestamp")
    updated_at: datetime = Field(..., description="Book last update timestamp")


class BookVersionBase(BaseModel):
    """Base BookVersion schema with common fields."""

    book_id: UUID = Field(..., description="Book identifier")
    version_number: int = Field(..., description="Version number")
    status: str = Field(..., max_length=50, description="Version status")
    s3_md_key: str | None = Field(None, max_length=255, description="S3 markdown key")
    s3_pdf_key: str | None = Field(None, max_length=255, description="S3 PDF key")
    checksum: str | None = Field(None, max_length=64, description="Content checksum")
    rendered_at: datetime | None = Field(None, description="Rendering completion timestamp")


class BookVersionCreate(BookVersionBase):
    """Schema for creating a new book version."""

    pass


class BookVersionUpdate(BaseModel):
    """Schema for updating a book version."""

    status: str | None = Field(None, max_length=50, description="Version status")
    s3_md_key: str | None = Field(None, max_length=255, description="S3 markdown key")
    s3_pdf_key: str | None = Field(None, max_length=255, description="S3 PDF key")
    checksum: str | None = Field(None, max_length=64, description="Content checksum")
    rendered_at: datetime | None = Field(None, description="Rendering completion timestamp")


class BookVersionResponse(BookVersionBase):
    """Schema for book version responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Book version unique identifier")
    created_at: datetime = Field(..., description="Book version creation timestamp")
    updated_at: datetime | None = Field(None, description="Content last update timestamp")
