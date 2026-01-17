"""Snippet analysis domain model."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base
from app.db.utils import utc_now


class SnippetAnalysis(Base):
    """Analysis results for snippets."""

    __tablename__ = "snippet_analysis"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    world_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    snippet_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)

    contradiction_score: Mapped[float | None] = mapped_column(nullable=True)
    contains_claim_about_canon_entities: Mapped[bool] = mapped_column(default=False)
    analysis_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    analyzed_by: Mapped[str] = mapped_column(String(50), default="manual", nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now, nullable=False
    )

    def __repr__(self) -> str:
        return f"<SnippetAnalysis snippet={self.snippet_id} contradiction_score={self.contradiction_score}>"
