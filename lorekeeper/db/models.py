"""
Database models for LoreKeeper.
"""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from lorekeeper.db.database import Base
from lorekeeper.db.utils import utc_now


class World(Base):
    """World (campaign/setting) model."""

    __tablename__ = "world"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now, nullable=False
    )

    def __repr__(self) -> str:
        return f"<World id={self.id} name={self.name}>"


class Entity(Base):
    """Entity (canonical truth) model."""

    __tablename__ = "entity"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    world_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    type: Mapped[str] = mapped_column(String(100), nullable=False)
    canonical_name: Mapped[str] = mapped_column(String(255), nullable=False)
    aliases: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)
    summary: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="ACTIVE", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now, nullable=False
    )

    def __repr__(self) -> str:
        return f"<Entity id={self.id} name={self.canonical_name} type={self.type}>"


class Document(Base):
    """Document (mythic or strict source text) model."""

    __tablename__ = "document"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    world_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    mode: Mapped[str] = mapped_column(String(50), nullable=False)  # STRICT or MYTHIC
    kind: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    author: Mapped[str | None] = mapped_column(String(255), nullable=True)
    in_world_date: Mapped[str | None] = mapped_column(String(255), nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    provenance: Mapped[dict[str, object] | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now, nullable=False
    )

    def __repr__(self) -> str:
        return f"<Document id={self.id} title={self.title} mode={self.mode}>"


class DocumentSnippet(Base):
    """Document snippet model for retrieval."""

    __tablename__ = "document_snippet"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    document_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    world_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    snippet_index: Mapped[int] = mapped_column(nullable=False)
    start_char: Mapped[int] = mapped_column(nullable=False)
    end_char: Mapped[int] = mapped_column(nullable=False)
    snippet_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    def __repr__(self) -> str:
        return f"<DocumentSnippet id={self.id} document_id={self.document_id}>"


class EntityMention(Base):
    """Entity mention linking model."""

    __tablename__ = "entity_mention"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    snippet_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    entity_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    mention_text: Mapped[str] = mapped_column(String(255), nullable=False)
    confidence: Mapped[float] = mapped_column(nullable=False, default=1.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    def __repr__(self) -> str:
        return f"<EntityMention id={self.id} entity_id={self.entity_id}>"
