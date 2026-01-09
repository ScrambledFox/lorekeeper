"""
Service for detecting contradictions during claim ingestion.

Contradictions are assessed when lore is created, not stored as DB objects.
- CANON_TRUE claims: Rejected if they contradict with existing claims
- CANON_FALSE claims: Checked inversely; rejected if the lie is actually true
"""

from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from lorekeeper.api.schemas import ClaimCreate
from lorekeeper.db.models import Claim, ClaimTruth


async def check_claim_contradictions(
    claim_create: ClaimCreate,
    world_id: UUID,
    session: AsyncSession,
) -> str | None:
    """
    Check if a new claim contradicts existing canonical claims.

    Returns:
        None if claim is valid
        Error message (str) if claim should be rejected (409 Conflict)
    """

    if claim_create.truth_status == ClaimTruth.CANON_TRUE:
        return await _check_canon_true_claim(claim_create, world_id, session)
    elif claim_create.truth_status == ClaimTruth.CANON_FALSE:
        return await _check_canon_false_claim(claim_create, world_id, session)

    return None


async def _check_canon_true_claim(
    claim_create: ClaimCreate,
    world_id: UUID,
    session: AsyncSession,
) -> str | None:
    """
    For factual (CANON_TRUE) claims:
    Check if this claim contradicts:
    1. Existing CANON_FALSE claims with similar (subject, predicate)
    2. Existing CANON_TRUE claims with similar (subject, predicate) but different object_text
    Reject if contradiction found.

    Returns:
        A detail message if contradiction found with confidence rating, else None.
    """

    # First, find potentially contradictory CANON_FALSE claims
    # (same subject & predicate, opposite truth value)
    query = select(Claim).where(
        and_(
            Claim.world_id == world_id,
            Claim.subject_entity_id == claim_create.subject_entity_id,
            Claim.predicate == claim_create.predicate,
            Claim.truth_status == ClaimTruth.CANON_FALSE,  # Direct contradiction
        )
    )
    result = await session.execute(query)
    contradictory_false_claims = result.scalars().all()

    if contradictory_false_claims:
        existing_claim = contradictory_false_claims[0]
        return (
            f"Lore inconsistency: New CANON_TRUE claim contradicts existing "
            f"CANON_FALSE claim (id: {existing_claim.id}). {existing_claim.notes or ''}"
        )

    # Second, check for conflicting CANON_TRUE claims with the same predicate
    # but different object_text (e.g., "died in 1032" vs "died in 1050")
    if claim_create.object_text:
        query = select(Claim).where(
            and_(
                Claim.world_id == world_id,
                Claim.subject_entity_id == claim_create.subject_entity_id,
                Claim.predicate == claim_create.predicate,
                Claim.truth_status == ClaimTruth.CANON_TRUE,
                Claim.object_text != claim_create.object_text,
            )
        )
        result = await session.execute(query)
        conflicting_true_claims = result.scalars().all()

        if conflicting_true_claims:
            existing_claim = conflicting_true_claims[0]
            return (
                f"Lore inconsistency: New CANON_TRUE claim with different details contradicts "
                f"existing CANON_TRUE claim (id: {existing_claim.id}): {existing_claim.object_text or ''}"
            )

    return None


async def _check_canon_false_claim(
    claim_create: ClaimCreate,
    world_id: UUID,
    session: AsyncSession,
) -> str | None:
    """
    For non-factual (CANON_FALSE) claims (lies, myths):
    Check if the claim is actually true in canon.
    If a CANON_TRUE version of this claim exists, reject the CANON_FALSE version.

    This prevents contradictions like:
    - CANON_TRUE: "King Aldren died in Year 1032"
    - CANON_FALSE: "King Aldren is alive"  <- This should be rejected because the truth is he died
    """

    # Find if this same claim exists as CANON_TRUE
    query = select(Claim).where(
        and_(
            Claim.world_id == world_id,
            Claim.subject_entity_id == claim_create.subject_entity_id,
            Claim.predicate == claim_create.predicate,
            Claim.truth_status == ClaimTruth.CANON_TRUE,  # Truth exists
        )
    )
    result = await session.execute(query)
    true_version = result.scalar_one_or_none()

    if true_version:
        return (
            f"Lore inconsistency: Cannot mark as CANON_FALSE (myth/lie) because "
            f"the canonical truth already exists (id: {true_version.id}): {true_version.object_text or ''}"
        )

    return None
