from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base
from app.utils.datetime import utc_now


class BookVersionStatus:
    """Enumeration of possible book version statuses."""

    DRAFT = "DRAFT"
    READY_FOR_RENDER = "READY_FOR_RENDER"
    RENDERING = "RENDERING"
    RENDERED = "RENDERED"
    FAILED = "FAILED"


class Book(Base):
    """A book written in the world."""

    __tablename__ = "books"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    world_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    writer_ids: Mapped[list[UUID | None]] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    meta: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now, nullable=False
    )


class BookVersion(Base):
    """A specific version of a book."""

    __tablename__ = "book_versions"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    book_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    version_number: Mapped[int] = mapped_column(nullable=False)
    status: Mapped[BookVersionStatus] = mapped_column(String(50), nullable=False)
    s3_md_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    s3_pdf_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    rendered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
