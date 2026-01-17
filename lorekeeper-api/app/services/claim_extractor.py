"""
Service for extracting claims from document snippets.

This is the MVP implementation. Phase 3+ can add LLM-based extraction.
"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.domain import Claim, ClaimTruth, DocumentSnippet, EntityMention


def extract_claims_from_snippet(
    snippet_id: UUID,
    world_id: UUID,
    db: Session,
    strategy: str = "mention_based",
) -> list[Claim]:
    """
    Extract claims from a snippet based on entity mentions.

    MVP strategy: For each entity mentioned in the snippet, create an UNKNOWN claim.
    Phase 3+: Use LLM to extract subject-predicate-object triples.
    """

    snippet = db.query(DocumentSnippet).filter(DocumentSnippet.id == snippet_id).first()
    if not snippet:
        return []

    if strategy == "mention_based":
        # Get all entity mentions in this snippet
        mentions = db.query(EntityMention).filter(EntityMention.snippet_id == snippet_id).all()

        claims: list[Claim] = []
        for mention in mentions:
            # Create a generic "mentioned_in_document" claim
            claim = Claim(
                world_id=world_id,
                snippet_id=snippet_id,
                subject_entity_id=mention.entity_id,
                predicate="mentioned_in_document",
                object_text=snippet.snippet_text[:100],  # First 100 chars
                truth_status=ClaimTruth.CANON_TRUE,
                notes=f"Extracted from entity mention: {mention.mention_text}",
            )
            claims.append(claim)

        db.add_all(claims)
        db.commit()
        return claims

    return []
