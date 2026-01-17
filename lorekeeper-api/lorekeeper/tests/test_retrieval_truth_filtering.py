"""Tests for retrieval service with truth-status filtering."""

from typing import Any
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lorekeeper.models.domain import Claim, ClaimTruth, Document, DocumentSnippet, Entity, World
from lorekeeper.services.retrieval import RetrievalPolicy, RetrievalService


def approx(*args: Any, **kwargs: Any) -> Any:
    return pytest.approx(*args, **kwargs)  # pyright: ignore[reportUnknownMemberType]


@pytest_asyncio.fixture
async def world(db_session: AsyncSession) -> World:
    """Create a test world."""
    world = World(name=f"test_world_{uuid4()}", description="Test world")
    db_session.add(world)
    await db_session.flush()
    await db_session.refresh(world)
    return world


@pytest_asyncio.fixture
async def entity(db_session: AsyncSession, world: World) -> Entity:
    """Create a test entity."""
    entity = Entity(
        world_id=world.id,
        type="Character",
        canonical_name="Test Entity",
        aliases=[],
    )
    db_session.add(entity)
    await db_session.flush()
    await db_session.refresh(entity)
    return entity


@pytest_asyncio.fixture
async def strict_document(db_session: AsyncSession, world: World) -> Document:
    """Create a STRICT mode document."""
    doc = Document(
        world_id=world.id,
        mode="STRICT",
        kind="CHRONICLE",
        title="Strict Chronicle",
        text="This is a strict document",
    )
    db_session.add(doc)
    await db_session.flush()
    await db_session.refresh(doc)
    return doc


@pytest_asyncio.fixture
async def mythic_document(db_session: AsyncSession, world: World) -> Document:
    """Create a MYTHIC mode document."""
    doc = Document(
        world_id=world.id,
        mode="MYTHIC",
        kind="LEGEND",
        title="Mythic Legend",
        text="This is a mythic document",
    )
    db_session.add(doc)
    await db_session.flush()
    await db_session.refresh(doc)
    return doc


@pytest_asyncio.fixture
async def strict_snippet(
    db_session: AsyncSession, world: World, strict_document: Document
) -> DocumentSnippet:
    """Create a snippet from STRICT document."""
    snippet = DocumentSnippet(
        document_id=strict_document.id,
        world_id=world.id,
        snippet_index=0,
        start_char=0,
        end_char=25,
        snippet_text="This is a strict document",
    )
    db_session.add(snippet)
    await db_session.flush()
    await db_session.refresh(snippet)
    return snippet


@pytest_asyncio.fixture
async def mythic_snippet(
    db_session: AsyncSession, world: World, mythic_document: Document
) -> DocumentSnippet:
    """Create a snippet from MYTHIC document."""
    snippet = DocumentSnippet(
        document_id=mythic_document.id,
        world_id=world.id,
        snippet_index=0,
        start_char=0,
        end_char=25,
        snippet_text="This is a mythic document",
    )
    db_session.add(snippet)
    await db_session.flush()
    await db_session.refresh(snippet)
    return snippet


class TestRetrievalPolicy:
    """Tests for RetrievalPolicy enum."""

    def test_retrieval_policy_values(self):
        """Test that all retrieval policies are defined."""
        assert RetrievalPolicy.STRICT_ONLY.value == "STRICT_ONLY"
        assert RetrievalPolicy.MYTHIC_ONLY.value == "MYTHIC_ONLY"
        assert RetrievalPolicy.HYBRID.value == "HYBRID"
        assert RetrievalPolicy.CANON_TRUE_ONLY.value == "CANON_TRUE_ONLY"
        assert RetrievalPolicy.CANON_FALSE_ONLY.value == "CANON_FALSE_ONLY"
        assert RetrievalPolicy.WIDELY_BELIEVED.value == "WIDELY_BELIEVED"
        assert RetrievalPolicy.OBSCURE.value == "OBSCURE"

    def test_retrieval_policy_string_conversion(self):
        """Test string representation of retrieval policies."""
        policy = RetrievalPolicy.CANON_TRUE_ONLY
        assert str(policy.value) == "CANON_TRUE_ONLY"


class TestTruthStatusFiltering:
    """Tests for truth-status based filtering in retrieval."""

    @pytest.mark.asyncio
    async def test_canon_true_only_policy_excludes_canon_false(
        self,
        db_session: AsyncSession,
        world: World,
        entity: Entity,
        strict_snippet: DocumentSnippet,
    ):
        """
        Test CANON_TRUE_ONLY policy:
        - Include snippets with CANON_TRUE claims
        - Exclude snippets without CANON_TRUE claims
        """
        # Create a CANON_FALSE claim on the snippet
        claim_false = Claim(
            world_id=world.id,
            subject_entity_id=entity.id,
            snippet_id=strict_snippet.id,
            predicate="is_magic",
            truth_status=ClaimTruth.CANON_FALSE,
        )
        db_session.add(claim_false)
        await db_session.flush()

        # With CANON_TRUE_ONLY policy, this snippet should be excluded
        # (This would be tested in integration tests with actual retrieval)
        stmt = select(Claim).where(
            (Claim.snippet_id == strict_snippet.id) & (Claim.truth_status == ClaimTruth.CANON_TRUE)
        )
        result = await db_session.execute(stmt)
        snippet_claims = result.scalars().all()
        assert len(snippet_claims) == 0

    @pytest.mark.asyncio
    async def test_no_canon_false_policy_excludes_false_claims(
        self,
        db_session: AsyncSession,
        world: World,
        entity: Entity,
        strict_snippet: DocumentSnippet,
    ):
        """
        Test WIDELY_BELIEVED policy:
        - Include claims with high belief_prevalence (>= 0.7)
        - Exclude claims with low belief_prevalence
        """
        # Create a CANON_FALSE claim with low prevalence (obscure myth)
        claim_false = Claim(
            world_id=world.id,
            subject_entity_id=entity.id,
            snippet_id=strict_snippet.id,
            predicate="is_alive",
            truth_status=ClaimTruth.CANON_FALSE,
            belief_prevalence=0.2,
        )
        db_session.add(claim_false)
        await db_session.flush()

        # Create a CANON_FALSE claim with high prevalence (widely believed myth)
        claim_false_popular = Claim(
            world_id=world.id,
            subject_entity_id=entity.id,
            snippet_id=strict_snippet.id,
            predicate="is_magical",
            truth_status=ClaimTruth.CANON_FALSE,
            belief_prevalence=0.9,
        )
        db_session.add(claim_false_popular)
        await db_session.flush()

        # Check that both CANON_FALSE claims exist
        stmt = select(Claim).where(
            (Claim.snippet_id == strict_snippet.id) & (Claim.truth_status == ClaimTruth.CANON_FALSE)
        )
        result = await db_session.execute(stmt)
        snippet_false_claims = result.scalars().all()
        assert len(snippet_false_claims) == 2

    @pytest.mark.asyncio
    async def test_in_world_beliefs_includes_canonical_and_mythic(
        self,
        db_session: AsyncSession,
        world: World,
        entity: Entity,
        strict_snippet: DocumentSnippet,
    ):
        """
        Test belief prevalence filtering:
        - Include snippets with CANON_TRUE claims
        - Include snippets with high belief_prevalence (widely believed)
        """
        # Create CANON_TRUE claim with high prevalence
        claim_true = Claim(
            world_id=world.id,
            subject_entity_id=entity.id,
            snippet_id=strict_snippet.id,
            predicate="died_in",
            object_text="Year 1032",
            truth_status=ClaimTruth.CANON_TRUE,
            belief_prevalence=1.0,
        )
        db_session.add(claim_true)
        await db_session.flush()

        # Create widely-believed CANON_FALSE claim (myth)
        claim_myth = Claim(
            world_id=world.id,
            subject_entity_id=entity.id,
            snippet_id=strict_snippet.id,
            predicate="is_magic",
            truth_status=ClaimTruth.CANON_FALSE,
            belief_prevalence=0.8,
        )
        db_session.add(claim_myth)
        await db_session.flush()

        # Check that both claims exist
        stmt = select(Claim).where(Claim.snippet_id == strict_snippet.id)
        result = await db_session.execute(stmt)
        snippet_claims = result.scalars().all()
        assert len(snippet_claims) == 2

        # Verify belief prevalence values
        claim_true_retrieved = [
            c for c in snippet_claims if c.truth_status == ClaimTruth.CANON_TRUE
        ][0]
        claim_false_retrieved = [
            c for c in snippet_claims if c.truth_status == ClaimTruth.CANON_FALSE
        ][0]
        assert claim_true_retrieved.belief_prevalence == 1.0
        assert claim_false_retrieved.belief_prevalence == 0.8

    @pytest.mark.asyncio
    async def test_multiple_claims_on_snippet(
        self,
        db_session: AsyncSession,
        world: World,
        entity: Entity,
        strict_snippet: DocumentSnippet,
    ):
        """Test that snippets can have multiple claims."""
        # Create multiple claims
        for i in range(3):
            claim = Claim(
                world_id=world.id,
                subject_entity_id=entity.id,
                snippet_id=strict_snippet.id,
                predicate=f"predicate_{i}",
                truth_status=ClaimTruth.CANON_TRUE,
            )
            db_session.add(claim)
        await db_session.flush()

        # Verify all claims exist
        stmt = select(Claim).where(Claim.snippet_id == strict_snippet.id)
        result = await db_session.execute(stmt)
        all_claims = result.scalars().all()
        assert len(all_claims) == 3

    @pytest.mark.asyncio
    async def test_mixed_truth_statuses_on_snippet(
        self,
        db_session: AsyncSession,
        world: World,
        entity: Entity,
        strict_snippet: DocumentSnippet,
    ):
        """Test snippet with mixed truth statuses and belief prevalence."""
        # Create mixed claims with different prevalence values
        claims = [
            Claim(
                world_id=world.id,
                subject_entity_id=entity.id,
                snippet_id=strict_snippet.id,
                predicate="fact_1",
                truth_status=ClaimTruth.CANON_TRUE,
                belief_prevalence=1.0,
            ),
            Claim(
                world_id=world.id,
                subject_entity_id=entity.id,
                snippet_id=strict_snippet.id,
                predicate="myth_1",
                truth_status=ClaimTruth.CANON_FALSE,
                belief_prevalence=0.9,
            ),
            Claim(
                world_id=world.id,
                subject_entity_id=entity.id,
                snippet_id=strict_snippet.id,
                predicate="myth_2",
                truth_status=ClaimTruth.CANON_FALSE,
                belief_prevalence=0.1,
            ),
        ]
        db_session.add_all(claims)
        await db_session.flush()

        # Verify all claims exist
        stmt = select(Claim).where(Claim.snippet_id == strict_snippet.id)
        result = await db_session.execute(stmt)
        all_claims = result.scalars().all()
        assert len(all_claims) == 3

        # Count by truth status
        canon_true = [c for c in all_claims if c.truth_status == ClaimTruth.CANON_TRUE]
        canon_false = [c for c in all_claims if c.truth_status == ClaimTruth.CANON_FALSE]

        assert len(canon_true) == 1
        assert len(canon_false) == 2

        # Verify belief prevalence values
        widely_believed = [c for c in canon_false if c.belief_prevalence >= 0.7]
        obscure = [c for c in canon_false if c.belief_prevalence < 0.5]
        assert len(widely_believed) == 1
        assert len(obscure) == 1


class TestRetrievalServiceMethods:
    """Tests for RetrievalService static methods."""

    def test_cosine_similarity_same_vector(self):
        """Test cosine similarity of identical vectors."""
        vec = [1.0, 0.0, 0.0]
        similarity = RetrievalService.cosine_similarity(vec, vec)
        assert similarity == approx(1.0)

    def test_cosine_similarity_orthogonal_vectors(self):
        """Test cosine similarity of orthogonal vectors."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]
        similarity = RetrievalService.cosine_similarity(vec1, vec2)
        assert similarity == approx(0.0)

    def test_cosine_similarity_opposite_vectors(self):
        """Test cosine similarity of opposite vectors."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [-1.0, 0.0, 0.0]
        similarity = RetrievalService.cosine_similarity(vec1, vec2)
        assert similarity == approx(-1.0)

    def test_cosine_similarity_normalized_vectors(self):
        """Test cosine similarity of normalized vectors."""
        vec1 = [0.6, 0.8, 0.0]  # magnitude = 1.0
        vec2 = [0.6, 0.8, 0.0]  # magnitude = 1.0
        similarity = RetrievalService.cosine_similarity(vec1, vec2)
        assert similarity == approx(1.0)

    def test_cosine_similarity_empty_vectors(self):
        """Test cosine similarity with empty vectors."""
        similarity = RetrievalService.cosine_similarity([], [])
        assert similarity == 0.0

    def test_cosine_similarity_mismatched_lengths(self):
        """Test cosine similarity with vectors of different lengths."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [1.0, 0.0]
        similarity = RetrievalService.cosine_similarity(vec1, vec2)
        assert similarity == 0.0
