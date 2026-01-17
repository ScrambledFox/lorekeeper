from datetime import datetime
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base
from app.utils.datetime import utc_now


class SourceType:
    """Enumeration of possible source types."""

    BOOK = "BOOK"
    CHAPTER = "CHAPTER"
    ARTICLE = "ARTICLE"
    ORAL_TRADITION = "ORAL_TRADITION"
    INSCRIPTION = "INSCRIPTION"
    ARCHIVE = "ARCHIVE"
    RESEARCH_NOTE = "RESEARCH_NOTE"
    SONG = "SONG"
    OTHER = "OTHER"


class Source(Base):
    """A source of information for claims and entities."""

    __tablename__ = "source"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    world_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    type: Mapped[SourceType] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    author_ids: Mapped[list[UUID]] = mapped_column(
        ARRAY(PG_UUID(as_uuid=True)),
        nullable=False,
    )
    origin: Mapped[str | None] = mapped_column(String(255), nullable=True)
    book_version_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    meta: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)


class SourceChunk(Base):
    """A chunk of content from a source."""

    __tablename__ = "source_chunk"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    source_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    chunk_index: Mapped[int] = mapped_column(nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector, nullable=False)
    meta: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
