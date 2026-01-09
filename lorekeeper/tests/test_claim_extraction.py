"""
Tests for Claim model and claim-related functionality.

Note: The claim_extractor service uses sync Session API (not AsyncSession).
These tests focus on the Claim model and database operations.
The claim extraction service is tested in the existing test_claims.py file.
"""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lorekeeper.db.models import Claim, ClaimTruth, DocumentSnippet, Entity, EntityMention, World


@pytest.mark.asyncio
class TestClaimCreation:
    """Tests for claim creation and storage."""

    async def test_create_claim_with_subject_and_object_text(
        self,
        db_session: AsyncSession,
        test_world: World,
        test_entity: Entity,
    ) -> None:
        """Test creating a claim with subject entity and object text."""
        claim = Claim(
            world_id=test_world.id,
            subject_entity_id=test_entity.id,
            predicate="has_residence",
            object_text="Northern Kingdoms",
            truth_status=ClaimTruth.CANON_TRUE,
        )
        db_session.add(claim)
        await db_session.flush()
        await db_session.refresh(claim)

        assert claim.id is not None
        assert claim.subject_entity_id == test_entity.id
        assert claim.predicate == "has_residence"
        assert claim.object_text == "Northern Kingdoms"

    async def test_create_claim_with_subject_and_object_entity(
        self,
        db_session: AsyncSession,
        test_world: World,
        test_entity: Entity,
    ) -> None:
        """Test creating a claim with both subject and object as entities."""
        entity2 = Entity(
            world_id=test_world.id,
            type="Location",
            canonical_name="TestLand",
            aliases=["Land"],
            summary="A location",
            description="A test location",
            tags=[],
        )
        db_session.add(entity2)
        await db_session.flush()

        claim = Claim(
            world_id=test_world.id,
            subject_entity_id=test_entity.id,
            predicate="rules",
            object_entity_id=entity2.id,
            truth_status=ClaimTruth.CANON_TRUE,
        )
        db_session.add(claim)
        await db_session.flush()
        await db_session.refresh(claim)

        assert claim.subject_entity_id == test_entity.id
        assert claim.object_entity_id == entity2.id

    async def test_create_claim_from_snippet(
        self,
        db_session: AsyncSession,
        test_world: World,
        test_entity: Entity,
        test_document_snippet: DocumentSnippet,
    ) -> None:
        """Test creating a claim associated with a snippet."""
        claim = Claim(
            world_id=test_world.id,
            snippet_id=test_document_snippet.id,
            subject_entity_id=test_entity.id,
            predicate="mentioned_in_document",
            object_text=test_document_snippet.snippet_text[:100],
            truth_status=ClaimTruth.CANON_TRUE,
            notes="Test claim from snippet",
        )
        db_session.add(claim)
        await db_session.flush()
        await db_session.refresh(claim)

        assert claim.id is not None
        assert claim.snippet_id == test_document_snippet.id
        assert claim.predicate == "mentioned_in_document"


@pytest.mark.asyncio
class TestClaimTruthStatus:
    """Tests for claim truth status."""

    async def test_claim_truth_status_canon_true(
        self,
        db_session: AsyncSession,
        test_world: World,
        test_entity: Entity,
    ) -> None:
        """Test creating a claim with CANON_TRUE truth status."""
        claim = Claim(
            world_id=test_world.id,
            subject_entity_id=test_entity.id,
            predicate="is_good",
            object_text="Yes",
            truth_status=ClaimTruth.CANON_TRUE,
        )
        db_session.add(claim)
        await db_session.flush()
        await db_session.refresh(claim)

        assert claim.truth_status == ClaimTruth.CANON_TRUE

    async def test_claim_truth_status_canon_false(
        self,
        db_session: AsyncSession,
        test_world: World,
        test_entity: Entity,
    ) -> None:
        """Test creating a claim with CANON_FALSE truth status."""
        claim = Claim(
            world_id=test_world.id,
            subject_entity_id=test_entity.id,
            predicate="is_evil",
            object_text="False",
            truth_status=ClaimTruth.CANON_FALSE,
        )
        db_session.add(claim)
        await db_session.flush()
        await db_session.refresh(claim)

        assert claim.truth_status == ClaimTruth.CANON_FALSE


@pytest.mark.asyncio
class TestClaimBeliefPrevalence:
    """Tests for claim belief prevalence."""

    async def test_claim_belief_prevalence_default(
        self,
        db_session: AsyncSession,
        test_world: World,
        test_entity: Entity,
    ) -> None:
        """Test that claim belief_prevalence defaults to 0.5."""
        claim = Claim(
            world_id=test_world.id,
            subject_entity_id=test_entity.id,
            predicate="test",
            object_text="test",
        )
        db_session.add(claim)
        await db_session.flush()
        await db_session.refresh(claim)

        assert claim.belief_prevalence == 0.5

    async def test_claim_belief_prevalence_custom(
        self,
        db_session: AsyncSession,
        test_world: World,
        test_entity: Entity,
    ) -> None:
        """Test setting custom belief_prevalence."""
        claim = Claim(
            world_id=test_world.id,
            subject_entity_id=test_entity.id,
            predicate="rumored",
            object_text="test",
            belief_prevalence=0.2,
        )
        db_session.add(claim)
        await db_session.flush()
        await db_session.refresh(claim)

        assert claim.belief_prevalence == 0.2

    async def test_claim_belief_prevalence_high(
        self,
        db_session: AsyncSession,
        test_world: World,
        test_entity: Entity,
    ) -> None:
        """Test setting high belief_prevalence."""
        claim = Claim(
            world_id=test_world.id,
            subject_entity_id=test_entity.id,
            predicate="universally_known",
            object_text="test",
            belief_prevalence=0.95,
        )
        db_session.add(claim)
        await db_session.flush()
        await db_session.refresh(claim)

        assert claim.belief_prevalence == 0.95


@pytest.mark.asyncio
class TestClaimNotes:
    """Tests for claim notes."""

    async def test_claim_with_notes(
        self,
        db_session: AsyncSession,
        test_world: World,
        test_entity: Entity,
    ) -> None:
        """Test creating a claim with notes."""
        notes = "This claim is based on unreliable sources"
        claim = Claim(
            world_id=test_world.id,
            subject_entity_id=test_entity.id,
            predicate="test",
            object_text="test",
            notes=notes,
        )
        db_session.add(claim)
        await db_session.flush()
        await db_session.refresh(claim)

        assert claim.notes == notes

    async def test_claim_without_notes(
        self,
        db_session: AsyncSession,
        test_world: World,
        test_entity: Entity,
    ) -> None:
        """Test creating a claim without notes."""
        claim = Claim(
            world_id=test_world.id,
            subject_entity_id=test_entity.id,
            predicate="test",
            object_text="test",
        )
        db_session.add(claim)
        await db_session.flush()
        await db_session.refresh(claim)

        assert claim.notes is None


@pytest.mark.asyncio
class TestClaimQuerying:
    """Tests for querying and filtering claims."""

    async def test_query_claims_by_subject_entity(
        self,
        db_session: AsyncSession,
        test_world: World,
        test_entity: Entity,
    ) -> None:
        """Test querying claims by subject entity ID."""
        # Create multiple claims
        for i in range(3):
            claim = Claim(
                world_id=test_world.id,
                subject_entity_id=test_entity.id,
                predicate=f"predicate_{i}",
                object_text=f"object_{i}",
            )
            db_session.add(claim)
        await db_session.flush()

        # Query by subject
        result = await db_session.execute(
            select(Claim).where(Claim.subject_entity_id == test_entity.id)
        )
        claims = result.scalars().all()

        assert len(claims) >= 3

    async def test_query_claims_by_truth_status(
        self,
        db_session: AsyncSession,
        test_world: World,
        test_entity: Entity,
    ) -> None:
        """Test querying claims by truth status."""
        # Create claims with different truth statuses
        claim_true = Claim(
            world_id=test_world.id,
            subject_entity_id=test_entity.id,
            predicate="is_good",
            object_text="Yes",
            truth_status=ClaimTruth.CANON_TRUE,
        )
        claim_false = Claim(
            world_id=test_world.id,
            subject_entity_id=test_entity.id,
            predicate="is_evil",
            object_text="No",
            truth_status=ClaimTruth.CANON_FALSE,
        )
        db_session.add_all([claim_true, claim_false])
        await db_session.flush()

        # Query by truth status
        result = await db_session.execute(
            select(Claim).where(Claim.truth_status == ClaimTruth.CANON_TRUE)
        )
        true_claims = result.scalars().all()

        assert len(true_claims) >= 1
        for claim in true_claims:
            assert claim.truth_status == ClaimTruth.CANON_TRUE

    async def test_query_claims_by_world(
        self,
        db_session: AsyncSession,
        test_world: World,
        test_entity: Entity,
    ) -> None:
        """Test querying claims by world ID."""
        claim = Claim(
            world_id=test_world.id,
            subject_entity_id=test_entity.id,
            predicate="test",
            object_text="test",
        )
        db_session.add(claim)
        await db_session.flush()

        # Query by world
        result = await db_session.execute(select(Claim).where(Claim.world_id == test_world.id))
        claims = result.scalars().all()

        assert len(claims) >= 1

    async def test_query_claims_by_snippet(
        self,
        db_session: AsyncSession,
        test_world: World,
        test_entity: Entity,
        test_document_snippet: DocumentSnippet,
    ) -> None:
        """Test querying claims by snippet ID."""
        claim = Claim(
            world_id=test_world.id,
            snippet_id=test_document_snippet.id,
            subject_entity_id=test_entity.id,
            predicate="mentioned",
            object_text="in snippet",
        )
        db_session.add(claim)
        await db_session.flush()

        # Query by snippet
        result = await db_session.execute(
            select(Claim).where(Claim.snippet_id == test_document_snippet.id)
        )
        claims = result.scalars().all()

        assert len(claims) >= 1


class TestClaimEnums:
    """Tests for ClaimTruth enum."""

    def test_claim_truth_canon_true_value(self) -> None:
        """Test ClaimTruth.CANON_TRUE value."""
        assert ClaimTruth.CANON_TRUE == "CANON_TRUE"

    def test_claim_truth_canon_false_value(self) -> None:
        """Test ClaimTruth.CANON_FALSE value."""
        assert ClaimTruth.CANON_FALSE == "CANON_FALSE"

    def test_claim_truth_enum_members(self) -> None:
        """Test that ClaimTruth has expected members."""
        members = list(ClaimTruth)
        assert len(members) == 2
        assert ClaimTruth.CANON_TRUE in members
        assert ClaimTruth.CANON_FALSE in members


@pytest.mark.asyncio
class TestClaimRelationships:
    """Tests for claim relationships with other entities."""

    async def test_claim_with_mentioned_entity(
        self,
        db_session: AsyncSession,
        test_world: World,
        test_entity: Entity,
        test_document_snippet: DocumentSnippet,
    ) -> None:
        """Test creating a claim linked through entity mention."""
        # Create mention
        mention = EntityMention(
            snippet_id=test_document_snippet.id,
            entity_id=test_entity.id,
            mention_text="TestHero",
            confidence=0.95,
        )
        db_session.add(mention)
        await db_session.flush()

        # Create claim about mentioned entity
        claim = Claim(
            world_id=test_world.id,
            snippet_id=test_document_snippet.id,
            subject_entity_id=test_entity.id,
            predicate="appears_in",
            object_text="A document snippet",
        )
        db_session.add(claim)
        await db_session.flush()

        # Verify relationships
        result = await db_session.execute(
            select(Claim).where(
                Claim.snippet_id == test_document_snippet.id,
                Claim.subject_entity_id == test_entity.id,
            )
        )
        claims = result.scalars().all()
        assert len(claims) >= 1

    async def test_multiple_claims_same_subject(
        self,
        db_session: AsyncSession,
        test_world: World,
        test_entity: Entity,
    ) -> None:
        """Test creating multiple claims about same subject."""
        predicates = ["is_brave", "is_strong", "is_wise"]

        for pred in predicates:
            claim = Claim(
                world_id=test_world.id,
                subject_entity_id=test_entity.id,
                predicate=pred,
                object_text="Yes",
            )
            db_session.add(claim)

        await db_session.flush()

        result = await db_session.execute(
            select(Claim).where(Claim.subject_entity_id == test_entity.id)
        )
        claims = result.scalars().all()

        assert len(claims) >= len(predicates)
        assert all(c.subject_entity_id == test_entity.id for c in claims)
