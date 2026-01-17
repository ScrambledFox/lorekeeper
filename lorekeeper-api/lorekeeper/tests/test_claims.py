"""
Unit tests for Claim and SnippetAnalysis models.
"""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lorekeeper.models.domain import (
    Claim,
    ClaimTruth,
    DocumentSnippet,
    Entity,
    SnippetAnalysis,
    World,
)


@pytest.mark.asyncio
class TestClaimModel:
    """Tests for Claim model."""

    async def test_create_claim_canon_true(
        self, db_session: AsyncSession, test_world: World, test_entity: Entity
    ):
        """Test creating a CANON_TRUE claim."""
        claim = Claim(
            world_id=test_world.id,
            subject_entity_id=test_entity.id,
            predicate="died_in",
            object_text="Year 1032",
            truth_status=ClaimTruth.CANON_TRUE,
        )
        db_session.add(claim)
        await db_session.commit()

        query = select(Claim).where(Claim.id == claim.id)
        result = await db_session.execute(query)
        retrieved = result.scalar_one()
        assert retrieved.truth_status == ClaimTruth.CANON_TRUE
        assert retrieved.predicate == "died_in"
        assert retrieved.object_text == "Year 1032"

    async def test_create_claim_canon_false(
        self, db_session: AsyncSession, test_world: World, test_entity: Entity
    ):
        """Test creating a CANON_FALSE claim (myth/lie)."""
        claim = Claim(
            world_id=test_world.id,
            subject_entity_id=test_entity.id,
            predicate="is_alive",
            truth_status=ClaimTruth.CANON_FALSE,
            notes="A false rumor",
        )
        db_session.add(claim)
        await db_session.commit()

        query = select(Claim).where(Claim.id == claim.id)
        result = await db_session.execute(query)
        retrieved = result.scalar_one()
        assert retrieved.truth_status == ClaimTruth.CANON_FALSE
        assert retrieved.notes == "A false rumor"

    async def test_claim_timestamps(
        self, db_session: AsyncSession, test_world: World, test_entity: Entity
    ):
        """Test that claim timestamps are set."""
        from datetime import datetime

        claim = Claim(
            world_id=test_world.id,
            subject_entity_id=test_entity.id,
            predicate="test",
            truth_status=ClaimTruth.CANON_TRUE,
        )
        db_session.add(claim)
        await db_session.commit()

        query = select(Claim).where(Claim.id == claim.id)
        result = await db_session.execute(query)
        retrieved = result.scalar_one()
        assert isinstance(retrieved.created_at, datetime)
        assert isinstance(retrieved.updated_at, datetime)

    async def test_claim_repr(
        self, db_session: AsyncSession, test_world: World, test_entity: Entity
    ):
        """Test claim string representation."""
        claim = Claim(
            world_id=test_world.id,
            subject_entity_id=test_entity.id,
            predicate="died_in",
            object_text="Year 1032",
            truth_status=ClaimTruth.CANON_TRUE,
        )
        db_session.add(claim)
        await db_session.commit()

        repr_str = repr(claim)
        assert "Claim" in repr_str
        assert "died_in" in repr_str
        assert "CANON_TRUE" in repr_str

    async def test_filter_claims_by_truth_status(
        self, db_session: AsyncSession, test_world: World, test_entity: Entity
    ):
        """Test filtering claims by truth status."""
        # Create multiple claims
        for truth_status in [ClaimTruth.CANON_TRUE, ClaimTruth.CANON_TRUE, ClaimTruth.CANON_FALSE]:
            claim = Claim(
                world_id=test_world.id,
                subject_entity_id=test_entity.id,
                predicate=f"predicate_{truth_status}",
                truth_status=truth_status,
            )
            db_session.add(claim)
        await db_session.commit()

        # Filter by truth status
        query = select(Claim).where(
            Claim.world_id == test_world.id,
            Claim.truth_status == ClaimTruth.CANON_TRUE,
        )
        result = await db_session.execute(query)
        canon_true_claims = result.scalars().all()
        assert len(canon_true_claims) == 2

    async def test_filter_claims_by_entity(
        self, db_session: AsyncSession, test_world: World, test_entity: Entity
    ):
        """Test filtering claims by subject entity."""
        # Create another entity
        entity2 = Entity(
            world_id=test_world.id,
            type="Location",
            canonical_name="Test Location",
        )
        db_session.add(entity2)
        await db_session.flush()

        # Create claims for both entities
        claim1 = Claim(
            world_id=test_world.id,
            subject_entity_id=test_entity.id,
            predicate="test_predicate",
            truth_status=ClaimTruth.CANON_TRUE,
        )
        claim2 = Claim(
            world_id=test_world.id,
            subject_entity_id=entity2.id,
            predicate="test_predicate",
            truth_status=ClaimTruth.CANON_TRUE,
        )
        db_session.add_all([claim1, claim2])
        await db_session.commit()

        # Filter by entity
        query = select(Claim).where(
            Claim.world_id == test_world.id,
            Claim.subject_entity_id == test_entity.id,
        )
        result = await db_session.execute(query)
        entity_claims = result.scalars().all()
        assert len(entity_claims) == 1
        assert entity_claims[0].id == claim1.id


@pytest.mark.asyncio
class TestSnippetAnalysisModel:
    """Tests for SnippetAnalysis model."""

    async def test_create_snippet_analysis(
        self, db_session: AsyncSession, test_world: World, test_document_snippet: DocumentSnippet
    ):
        """Test creating snippet analysis."""
        analysis = SnippetAnalysis(
            world_id=test_world.id,
            snippet_id=test_document_snippet.id,
            contradiction_score=0.3,
            contains_claim_about_canon_entities=True,
            analysis_notes="Test analysis",
            analyzed_by="heuristic",
        )
        db_session.add(analysis)
        await db_session.commit()

        query = select(SnippetAnalysis).where(SnippetAnalysis.id == analysis.id)
        result = await db_session.execute(query)
        retrieved = result.scalar_one()
        assert retrieved.contradiction_score == 0.3
        assert retrieved.contains_claim_about_canon_entities is True
        assert retrieved.analyzed_by == "heuristic"

    async def test_snippet_analysis_defaults(
        self, db_session: AsyncSession, test_world: World, test_document_snippet: DocumentSnippet
    ):
        """Test snippet analysis default values."""
        analysis = SnippetAnalysis(
            world_id=test_world.id,
            snippet_id=test_document_snippet.id,
        )
        db_session.add(analysis)
        await db_session.commit()

        query = select(SnippetAnalysis).where(SnippetAnalysis.id == analysis.id)
        result = await db_session.execute(query)
        retrieved = result.scalar_one()
        assert retrieved.contains_claim_about_canon_entities is False
        assert retrieved.analyzed_by == "manual"
        assert retrieved.contradiction_score is None
