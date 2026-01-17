"""Entity domain model."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base
from app.utils.datetime import utc_now


class EntityType:
    """Enumeration of possible entity types."""

    PERSON = "PERSON"
    LOCATION = "LOCATION"
    FACTION = "FACTION"
    ORGANIZATION = "ORGANIZATION"
    ITEM = "ITEM"
    CREATURE = "CREATURE"
    EVENT = "EVENT"
    CONCEPT = "CONCEPT"
    ARTIFACT = "ARTIFACT"
    VEHICLE = "VEHICLE"
    OTHER = "OTHER"


class Entity(Base):
    """An Entity within the world."""

    __tablename__ = "entity"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    world_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    type: Mapped[EntityType] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    aliases: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)
    summary: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now, nullable=False
    )

    def __repr__(self) -> str:
        return f"<Entity id={self.id} name={self.canonical_name} type={self.type}>"


class EntityAlias(Base):
    """Aliases associated with an Entity."""

    __tablename__ = "entity_alias"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    entity_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    alias: Mapped[str] = mapped_column(String(255), nullable=False)
    locale: Mapped[str | None] = mapped_column(String(10), nullable=True)
    source_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)


class EntityTag(Base):
    """Tags associated with an Entity."""

    __tablename__ = "entity_tag"

    entity_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    tag_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
