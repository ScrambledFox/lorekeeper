"""World domain model."""

from datetime import datetime
from typing import TypedDict
from uuid import UUID, uuid4

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base
from app.utils.datetime import utc_now


class WorldMetadata(TypedDict, total=False):
    """Metadata for a world."""

    themes: list[str]  # e.g., ["dark fantasy", "steampunk"]
    era: str  # Global era, e.g., "medieval", "sci-fi"
    tags: list[str]  # Custom tags for categorization


class World(Base):
    """World (campaign/setting) model."""

    __tablename__ = "world"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[WorldMetadata | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now, nullable=False
    )

    def __repr__(self) -> str:
        return f"<World id={self.id} name={self.name}>"
