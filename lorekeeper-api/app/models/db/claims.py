"""Claim domain model."""

from datetime import datetime
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base
from app.utils.datetime import utc_now


class Claim(Base):
    """Claim (atomic statement) model."""

    __tablename__ = "claim"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    world_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)

    subject_entity_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    predicate: Mapped[str] = mapped_column(
        String(255), nullable=False
    )  # e.g., "is located in", "is allied with"
    object_entity_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    object_value: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True
    )  # e.g., {"amount": 100, "unit": "years"}

    canon_state: Mapped[str] = mapped_column(
        String(50), nullable=False, default="DRAFT"
    )  # e.g., "DRAFT", "ARCHIVED", "STRICT", "MYTHIC", "APOCRYPHAL"
    confidence: Mapped[float] = mapped_column(
        nullable=False, default=0.5
    )  # Confidence level (0.0 to 1.0). STRICT + 1.0 = believed facts, APOCRYPHAL + 0.0 = widely disputed untruths.

    asserted_by_entity_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)

    source_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True
    )  # Where the claim was first recorded, a book chapter, oral legend, research note, etc.

    created_by: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # user:joris, agent:lorebot, import:archive-12
    version_group_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), nullable=False, default=uuid4
    )  # Grouping for versioning of same conceptual claims. The city fell in 902 vs The city fell in 903.
    supersedes_claim_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True
    )  # Points to the claim that supersedes this one, if any.

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now, nullable=False
    )

    def __repr__(self) -> str:
        return f"<Claim subject={self.subject_entity_id} {self.predicate} {self.object_text or self.object_entity_id} [{self.truth_status}] (believed: {self.belief_prevalence:.1%})>"


class ClaimEmbedding(Base):
    """Embedding for a claim."""

    __tablename__ = "claim_embedding"

    claim_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True
    )  # One-to-one with Claim
    embedding: Mapped[list[float]] = mapped_column(
        Vector, nullable=False
    )  # Vector embedding of the claim text
    model: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # Model used to generate the embedding
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)


class ClaimTag(Base):
    """Tags associated with a Claim."""

    __tablename__ = "claim_tag"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    claim_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    tag_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
