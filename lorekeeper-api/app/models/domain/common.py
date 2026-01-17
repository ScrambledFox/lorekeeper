from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base
from app.utils.datetime import utc_now


class CanonState:
    """
    Enumeration of canonical states for lore entries.

    This doesn't indicate truthfulness, but rather the status of acceptance within the world's lore.
    """

    DRAFT = "DRAFT"  # Unreview or agent-pending proposal
    ARCHIVED = "ARCHIVED"  # Deprecated or no longer relevant
    STRICT = "STRICT"  # Strictly canonical e.g., historical fact
    MYTHIC = "MYTHIC"  # Folklore or legendary status, widely accepted
    APOCRYPHAL = "APOCRYPHAL"  # Widely disputed or false, propoganda, rumor, misinformation


class Tag(Base):
    """Tag model for categorizing entities and worlds."""

    __tablename__ = "tag"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    kind: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    def __repr__(self) -> str:
        return f"<Tag id={self.id} name={self.name}>"
