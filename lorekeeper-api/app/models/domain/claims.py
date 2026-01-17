"""Claim domain model."""

from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base
from app.db.utils import utc_now


class ClaimTruth(str, Enum):
    """Truth value for a claim."""

    CANON_TRUE = "CANON_TRUE"
    CANON_FALSE = "CANON_FALSE"


class Claim(Base):
    """Claim (atomic statement) model."""

    __tablename__ = "claim"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    world_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    snippet_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    claimed_by_entity_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)

    # Subject-Predicate-Object triple
    subject_entity_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    predicate: Mapped[str] = mapped_column(String(255), nullable=False)
    object_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    object_entity_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)

    # Truth value
    truth_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=ClaimTruth.CANON_TRUE
    )

    # Belief prevalence: How widely believed is this claim in the world?
    # 0.0 = Nobody believes it (obscure truth)
    # 0.5 = Moderately believed (some know it)
    # 1.0 = Universally believed (everyone thinks it's true)
    belief_prevalence: Mapped[float] = mapped_column(nullable=False, default=0.5)

    # Audit trail
    canon_ref_entity_version_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now, nullable=False
    )

    def __repr__(self) -> str:
        return f"<Claim subject={self.subject_entity_id} {self.predicate} {self.object_text or self.object_entity_id} [{self.truth_status}] (believed: {self.belief_prevalence:.1%})>"
