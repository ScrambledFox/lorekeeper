"""
Integration tests for claim API endpoints and contradiction detection.
"""

from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from lorekeeper.db.models import Claim, ClaimTruth, Document, DocumentSnippet, Entity, World


@pytest_asyncio.fixture
async def world(db_session: AsyncSession) -> World:
    """Create a test world."""
    world = World(name=f"test_world_{uuid4()}", description="Test world for claims")
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
        canonical_name="King Aldren",
        aliases=["Aldren"],
        summary="The late King of Aldren",
    )
    db_session.add(entity)
    await db_session.flush()
    await db_session.refresh(entity)
    return entity


@pytest_asyncio.fixture
async def snippet(db_session: AsyncSession, world: World) -> DocumentSnippet:
    """Create a test document snippet."""
    document = Document(
        world_id=world.id,
        mode="STRICT",
        kind="CHRONICLE",
        title="Test Chronicle",
        text="King Aldren died in Year 1032",
    )
    db_session.add(document)
    await db_session.flush()
    await db_session.refresh(document)

    snippet = DocumentSnippet(
        document_id=document.id,
        world_id=world.id,
        snippet_index=0,
        start_char=0,
        end_char=29,
        snippet_text="King Aldren died in Year 1032",
    )
    db_session.add(snippet)
    await db_session.flush()
    await db_session.refresh(snippet)
    return snippet


class TestClaimCRUD:
    """Tests for claim CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_claim(self, client: AsyncClient, world: World, entity: Entity):
        """Test creating a claim via API."""
        response = await client.post(
            f"/worlds/{world.id}/claims",
            json={
                "subject_entity_id": str(entity.id),
                "predicate": "died_in",
                "object_text": "Year 1032",
                "truth_status": "CANON_TRUE",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["truth_status"] == "CANON_TRUE"
        assert data["predicate"] == "died_in"
        assert data["object_text"] == "Year 1032"

    @pytest.mark.asyncio
    async def test_get_claim(
        self, client: AsyncClient, db_session: AsyncSession, world: World, entity: Entity
    ):
        """Test retrieving a claim."""
        # Create claim in DB
        claim = Claim(
            world_id=world.id,
            subject_entity_id=entity.id,
            predicate="died_in",
            object_text="Year 1032",
            truth_status=ClaimTruth.CANON_TRUE,
        )
        db_session.add(claim)
        await db_session.flush()
        await db_session.refresh(claim)

        # Retrieve via API
        response = await client.get(f"/worlds/{world.id}/claims/{claim.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(claim.id)
        assert data["predicate"] == "died_in"

    @pytest.mark.asyncio
    async def test_update_claim(
        self, client: AsyncClient, db_session: AsyncSession, world: World, entity: Entity
    ):
        """Test updating a claim."""
        # Create claim
        claim = Claim(
            world_id=world.id,
            subject_entity_id=entity.id,
            predicate="died_in",
            object_text="Year 1032",
            truth_status=ClaimTruth.CANON_TRUE,
            notes="Original note",
        )
        db_session.add(claim)
        await db_session.flush()
        await db_session.refresh(claim)

        # Update via API
        response = await client.patch(
            f"/worlds/{world.id}/claims/{claim.id}",
            json={"notes": "Updated note"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["notes"] == "Updated note"

    @pytest.mark.asyncio
    async def test_delete_claim(
        self, client: AsyncClient, db_session: AsyncSession, world: World, entity: Entity
    ):
        """Test deleting a claim."""
        # Create claim
        claim = Claim(
            world_id=world.id,
            subject_entity_id=entity.id,
            predicate="died_in",
            truth_status=ClaimTruth.CANON_TRUE,
        )
        db_session.add(claim)
        await db_session.flush()
        await db_session.refresh(claim)

        # Delete via API
        response = await client.delete(f"/worlds/{world.id}/claims/{claim.id}")
        assert response.status_code == 200

        # Verify deleted
        response = await client.get(f"/worlds/{world.id}/claims/{claim.id}")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_claims(
        self, client: AsyncClient, db_session: AsyncSession, world: World, entity: Entity
    ):
        """Test listing claims."""
        # Create multiple claims
        for i in range(3):
            claim = Claim(
                world_id=world.id,
                subject_entity_id=entity.id,
                predicate=f"predicate_{i}",
                truth_status=ClaimTruth.CANON_TRUE,
            )
            db_session.add(claim)
        await db_session.flush()

        # List via API
        response = await client.get(f"/worlds/{world.id}/claims")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 3

    @pytest.mark.asyncio
    async def test_list_claims_with_filter(
        self, client: AsyncClient, db_session: AsyncSession, world: World, entity: Entity
    ):
        """Test listing claims with filters."""
        # Create mixed claims
        claim1 = Claim(
            world_id=world.id,
            subject_entity_id=entity.id,
            predicate="test",
            truth_status=ClaimTruth.CANON_TRUE,
        )
        claim2 = Claim(
            world_id=world.id,
            subject_entity_id=entity.id,
            predicate="test",
            truth_status=ClaimTruth.CANON_FALSE,
        )
        db_session.add_all([claim1, claim2])
        await db_session.flush()

        # Filter by truth status
        response = await client.get(
            f"/worlds/{world.id}/claims", params={"truth_status": "CANON_TRUE"}
        )
        assert response.status_code == 200
        data = response.json()
        assert all(c["truth_status"] == "CANON_TRUE" for c in data)


class TestContradictionDetection:
    """Tests for contradiction detection during ingestion."""

    @pytest.mark.asyncio
    async def test_reject_canon_true_contradicting_canon_false(
        self, client: AsyncClient, db_session: AsyncSession, world: World, entity: Entity
    ):
        """
        Test: Creating a CANON_TRUE claim that contradicts existing CANON_FALSE should fail.
        """
        # First, create the false claim
        false_claim = Claim(
            world_id=world.id,
            subject_entity_id=entity.id,
            predicate="is_alive",
            truth_status=ClaimTruth.CANON_FALSE,
            notes="He's actually dead",
        )
        db_session.add(false_claim)
        await db_session.flush()

        # Now try to create the contradictory true claim
        response = await client.post(
            f"/worlds/{world.id}/claims",
            json={
                "subject_entity_id": str(entity.id),
                "predicate": "is_alive",
                "truth_status": "CANON_TRUE",
            },
        )

        assert response.status_code == 409
        assert "Lore inconsistency" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_reject_canon_false_when_truth_exists(
        self, client: AsyncClient, db_session: AsyncSession, world: World, entity: Entity
    ):
        """
        Test: Creating a CANON_FALSE claim when CANON_TRUE exists should fail.
        """
        # First, create the true claim
        true_claim = Claim(
            world_id=world.id,
            subject_entity_id=entity.id,
            predicate="died_in",
            object_text="Year 1032",
            truth_status=ClaimTruth.CANON_TRUE,
        )
        db_session.add(true_claim)
        await db_session.flush()

        # Now try to create a contradictory false claim
        response = await client.post(
            f"/worlds/{world.id}/claims",
            json={
                "subject_entity_id": str(entity.id),
                "predicate": "died_in",
                "object_text": "Year 1050",
                "truth_status": "CANON_FALSE",
                "notes": "False rumor about death year",
            },
        )

        assert response.status_code == 409
        assert "Lore inconsistency" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_allow_canon_true_without_contradictions(
        self, client: AsyncClient, world: World, entity: Entity
    ):
        """Test: Creating a CANON_TRUE claim with no contradictions succeeds."""
        response = await client.post(
            f"/worlds/{world.id}/claims",
            json={
                "subject_entity_id": str(entity.id),
                "predicate": "died_in",
                "object_text": "Year 1032",
                "truth_status": "CANON_TRUE",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["truth_status"] == "CANON_TRUE"

    @pytest.mark.asyncio
    async def test_allow_unknown_claims(self, client: AsyncClient, world: World, entity: Entity):
        """Test: Creating claims with low belief_prevalence (obscure/unknown status)."""
        response = await client.post(
            f"/worlds/{world.id}/claims",
            json={
                "subject_entity_id": str(entity.id),
                "predicate": "has_secret_treasure",
                "truth_status": "CANON_TRUE",
                "belief_prevalence": 0.1,
                "notes": "Only the Wizards of the Gray tower know this",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["truth_status"] == "CANON_TRUE"
        assert data["belief_prevalence"] == 0.1

    @pytest.mark.asyncio
    async def test_allow_multiple_canon_false_claims(
        self, client: AsyncClient, world: World, entity: Entity
    ):
        """Test: Multiple CANON_FALSE claims can coexist (they're just myths)."""
        # Create first false claim
        response1 = await client.post(
            f"/worlds/{world.id}/claims",
            json={
                "subject_entity_id": str(entity.id),
                "predicate": "is_alive",
                "truth_status": "CANON_FALSE",
            },
        )
        assert response1.status_code == 201

        # Create second false claim (different predicate)
        response2 = await client.post(
            f"/worlds/{world.id}/claims",
            json={
                "subject_entity_id": str(entity.id),
                "predicate": "is_magical",
                "truth_status": "CANON_FALSE",
            },
        )
        assert response2.status_code == 201


class TestClaimWorkflow:
    """Acceptance tests for complete claim workflows."""

    @pytest.mark.asyncio
    async def test_full_claim_truth_workflow(
        self, client: AsyncClient, db_session: AsyncSession, world: World, entity: Entity
    ):
        """
        Acceptance test: Create facts, rumors, verify contradictions are caught.

        Scenario:
        1. Create CANON_TRUE claim: "Aldren died in 1032" (succeeds)
        2. Try CANON_TRUE: "Aldren is alive" (fails - contradicts #1)
        3. Create CANON_FALSE myth: "He rules from beneath the lake" (widely believed - high prevalence)
        4. Create obscure CANON_TRUE: "His treasure is hidden" (only wizards know - low prevalence)
        """

        # 1. Create canon truth claim - should succeed
        response = await client.post(
            f"/worlds/{world.id}/claims",
            json={
                "subject_entity_id": str(entity.id),
                "predicate": "died_in",
                "object_text": "Year 1032",
                "truth_status": "CANON_TRUE",
                "belief_prevalence": 1.0,
            },
        )
        assert response.status_code == 201

        # 2. Try to create contradictory CANON_TRUE - should fail
        response = await client.post(
            f"/worlds/{world.id}/claims",
            json={
                "subject_entity_id": str(entity.id),
                "predicate": "died_in",
                "object_text": "Year 1050",
                "truth_status": "CANON_TRUE",
            },
        )
        assert response.status_code == 409

        # 3. Create CANON_FALSE myth - should succeed (widely believed)
        response = await client.post(
            f"/worlds/{world.id}/claims",
            json={
                "subject_entity_id": str(entity.id),
                "predicate": "rules_from_beneath_lake",
                "truth_status": "CANON_FALSE",
                "belief_prevalence": 0.9,
                "notes": "Popular myth - almost everyone believes this",
            },
        )
        assert response.status_code == 201

        # 4. Create obscure CANON_TRUE claim - should succeed
        response = await client.post(
            f"/worlds/{world.id}/claims",
            json={
                "subject_entity_id": str(entity.id),
                "predicate": "has_treasure_in_lake",
                "truth_status": "CANON_TRUE",
                "belief_prevalence": 0.1,
                "notes": "Only the Wizards of the Gray tower know this",
            },
        )
        assert response.status_code == 201

        # Verify all were created
        response = await client.get(f"/worlds/{world.id}/claims")
        assert response.status_code == 200
        claims = response.json()
        assert len(claims) >= 3
        predicates = [c["predicate"] for c in claims]
        assert "died_in" in predicates
        assert "rules_from_beneath_lake" in predicates
        assert "has_treasure_in_lake" in predicates
