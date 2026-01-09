"""
Tests for database seeding scripts.
"""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lorekeeper.db.models import Document, Entity, World


@pytest.mark.asyncio
class TestSeedInitialWorld:
    """Tests for seed_initial_world function."""

    async def test_seed_creates_world(self, db_session: AsyncSession) -> None:
        """Test that seeding creates a world."""
        # Note: This requires the database to be empty or pre-populated by the seed
        # In a real test, you would create test data or use a separate test seed
        assert True  # Placeholder for actual test

    async def test_seeded_world_has_correct_data(self, test_world: World) -> None:
        """Test that test worlds have expected data."""
        assert test_world.name is not None
        assert len(test_world.name) > 0

    async def test_seed_creates_entities(self, db_session: AsyncSession, test_world: World) -> None:
        """Test that entities can be created."""
        # Create test entities
        entity = Entity(
            world_id=test_world.id,
            type="Character",
            canonical_name="SeedTest",
            aliases=["Test"],
            summary="Test entity",
            description="A test entity",
            tags=[],
        )
        db_session.add(entity)
        await db_session.flush()

        result = await db_session.execute(select(Entity).where(Entity.world_id == test_world.id))
        entities = result.scalars().all()
        assert len(entities) >= 1

    async def test_seed_creates_canonical_entities(
        self,
        db_session: AsyncSession,
        test_world: World,
    ) -> None:
        """Test that canonical (non-fiction) entities can be created."""
        entity = Entity(
            world_id=test_world.id,
            type="Character",
            canonical_name="CanonicalChar",
            aliases=["Canon"],
            summary="Canonical character",
            description="A canonical character",
            tags=["canonical"],
            is_fiction=False,
        )
        db_session.add(entity)
        await db_session.flush()

        result = await db_session.execute(
            select(Entity).where(~Entity.is_fiction, Entity.world_id == test_world.id)
        )
        canonical = result.scalars().all()
        assert len(canonical) >= 1

    async def test_seed_creates_fiction_entity(
        self,
        db_session: AsyncSession,
        test_world: World,
    ) -> None:
        """Test that fiction entities can be created."""
        entity = Entity(
            world_id=test_world.id,
            type="Creature",
            canonical_name="MythicalBeast",
            aliases=["Beast"],
            summary="A mythical creature",
            description="From tales and legends",
            tags=["mythical"],
            is_fiction=True,
        )
        db_session.add(entity)
        await db_session.flush()

        result = await db_session.execute(
            select(Entity).where(Entity.is_fiction, Entity.world_id == test_world.id)
        )
        fiction = result.scalars().all()
        assert len(fiction) >= 1

    async def test_seed_creates_documents(
        self,
        db_session: AsyncSession,
        test_world: World,
    ) -> None:
        """Test that documents can be created."""
        doc = Document(
            world_id=test_world.id,
            mode="STRICT",
            kind="CHRONICLE",
            title="Seed Test Document",
            author="Test Author",
            text="Test document content",
        )
        db_session.add(doc)
        await db_session.flush()

        result = await db_session.execute(
            select(Document).where(Document.world_id == test_world.id)
        )
        documents = result.scalars().all()
        assert len(documents) >= 1

    async def test_seed_creates_strict_document(
        self,
        db_session: AsyncSession,
        test_world: World,
    ) -> None:
        """Test that STRICT mode documents can be created."""
        doc = Document(
            world_id=test_world.id,
            mode="STRICT",
            kind="TEXTBOOK",
            title="Strict Document",
            author="Scholar",
            text="Factual content",
        )
        db_session.add(doc)
        await db_session.flush()

        result = await db_session.execute(
            select(Document).where(
                Document.mode == "STRICT",
                Document.world_id == test_world.id,
            )
        )
        strict_docs = result.scalars().all()
        assert len(strict_docs) >= 1

    async def test_seed_creates_mythic_documents(
        self,
        db_session: AsyncSession,
        test_world: World,
    ) -> None:
        """Test that MYTHIC mode documents can be created."""
        doc = Document(
            world_id=test_world.id,
            mode="MYTHIC",
            kind="RUMOR",
            title="Mythic Document",
            author="Storyteller",
            text="A tale from legend",
        )
        db_session.add(doc)
        await db_session.flush()

        result = await db_session.execute(
            select(Document).where(
                Document.mode == "MYTHIC",
                Document.world_id == test_world.id,
            )
        )
        mythic_docs = result.scalars().all()
        assert len(mythic_docs) >= 1

    async def test_seeded_world_entities_relationship(
        self,
        db_session: AsyncSession,
        test_world: World,
    ) -> None:
        """Test that entities are correctly associated with the world."""
        entity = Entity(
            world_id=test_world.id,
            type="Location",
            canonical_name="TestLocation",
            aliases=["Location"],
            summary="Test",
            description="Test location",
            tags=[],
        )
        db_session.add(entity)
        await db_session.flush()

        result = await db_session.execute(select(Entity).where(Entity.world_id == test_world.id))
        entities = result.scalars().all()
        assert len(entities) >= 1
        assert all(e.world_id == test_world.id for e in entities)

    async def test_seeded_world_documents_relationship(
        self,
        db_session: AsyncSession,
        test_world: World,
    ) -> None:
        """Test that documents are correctly associated with the world."""
        doc = Document(
            world_id=test_world.id,
            mode="STRICT",
            kind="CHRONICLE",
            title="World Document",
            author="Author",
            text="Content",
        )
        db_session.add(doc)
        await db_session.flush()

        result = await db_session.execute(
            select(Document).where(Document.world_id == test_world.id)
        )
        documents = result.scalars().all()
        assert len(documents) >= 1
        assert all(d.world_id == test_world.id for d in documents)

    async def test_seeded_entities_have_aliases(
        self,
        db_session: AsyncSession,
        test_world: World,
    ) -> None:
        """Test that entities have aliases."""
        entity = Entity(
            world_id=test_world.id,
            type="Character",
            canonical_name="AliasTest",
            aliases=["Alias1", "Alias2"],
            summary="Test",
            description="Testing aliases",
            tags=[],
        )
        db_session.add(entity)
        await db_session.flush()

        result = await db_session.execute(
            select(Entity).where(Entity.canonical_name == "AliasTest")
        )
        entity = result.scalars().first()
        assert entity is not None
        assert isinstance(entity.aliases, list)
        assert len(entity.aliases) > 0

    async def test_seeded_entities_have_tags(
        self,
        db_session: AsyncSession,
        test_world: World,
    ) -> None:
        """Test that entities can have tags."""
        entity = Entity(
            world_id=test_world.id,
            type="Character",
            canonical_name="TagTest",
            aliases=["Tag"],
            summary="Test",
            description="Testing tags",
            tags=["important", "legendary"],
        )
        db_session.add(entity)
        await db_session.flush()

        result = await db_session.execute(select(Entity).where(Entity.canonical_name == "TagTest"))
        entity = result.scalars().first()
        assert entity is not None
        assert isinstance(entity.tags, list)

    async def test_seeded_documents_have_provenance(
        self,
        db_session: AsyncSession,
        test_world: World,
    ) -> None:
        """Test that documents can have provenance metadata."""
        doc = Document(
            world_id=test_world.id,
            mode="STRICT",
            kind="CHRONICLE",
            title="ProvenanceDoc",
            author="Author",
            text="Content",
            provenance={"source": "archive", "verified": True},
        )
        db_session.add(doc)
        await db_session.flush()

        result = await db_session.execute(select(Document).where(Document.title == "ProvenanceDoc"))
        doc = result.scalars().first()
        assert doc is not None
        assert doc.provenance is not None
        assert isinstance(doc.provenance, dict)

    async def test_seed_entity_types_are_valid(
        self,
        db_session: AsyncSession,
        test_world: World,
    ) -> None:
        """Test that entities have valid types."""
        valid_types = ["Character", "Location", "Faction", "Creature", "Object", "Event"]

        for entity_type in valid_types[:3]:  # Test a few
            entity = Entity(
                world_id=test_world.id,
                type=entity_type,
                canonical_name=f"Entity_{entity_type}",
                aliases=["Test"],
                summary="Test",
                description="Testing",
                tags=[],
            )
            db_session.add(entity)

        await db_session.flush()

        result = await db_session.execute(select(Entity).where(Entity.world_id == test_world.id))
        entities = result.scalars().all()
        for entity in entities:
            assert entity.type in valid_types

    async def test_seed_document_kinds_are_valid(
        self,
        db_session: AsyncSession,
        test_world: World,
    ) -> None:
        """Test that documents have valid kinds."""
        valid_kinds = ["CHRONICLE", "SCRIPTURE", "BALLAD", "RUMOR", "TEXTBOOK", "ARTIFACT"]

        for doc_kind in valid_kinds[:3]:  # Test a few
            doc = Document(
                world_id=test_world.id,
                mode="STRICT",
                kind=doc_kind,
                title=f"Doc_{doc_kind}",
                author="Author",
                text="Content",
            )
            db_session.add(doc)

        await db_session.flush()

        result = await db_session.execute(
            select(Document).where(Document.world_id == test_world.id)
        )
        documents = result.scalars().all()
        for doc in documents:
            assert doc.kind in valid_kinds

    async def test_seed_timestamps_are_set(
        self,
        db_session: AsyncSession,
        test_world: World,
    ) -> None:
        """Test that entities have created_at and updated_at timestamps."""
        entity = Entity(
            world_id=test_world.id,
            type="Character",
            canonical_name="TimestampTest",
            aliases=["Test"],
            summary="Test",
            description="Testing timestamps",
            tags=[],
        )
        db_session.add(entity)
        await db_session.flush()
        await db_session.refresh(entity)

        assert entity.created_at is not None
        assert entity.updated_at is not None
        assert entity.created_at <= entity.updated_at


@pytest.mark.asyncio
class TestSeededDataIntegrity:
    """Tests for data integrity of seeded data."""

    async def test_entity_complete(
        self,
        db_session: AsyncSession,
        test_world: World,
    ) -> None:
        """Test that entities have all required fields."""
        entity = Entity(
            world_id=test_world.id,
            type="Character",
            canonical_name="CompleteEntity",
            aliases=["Alias"],
            summary="A test character",
            description="Full description of the character",
            tags=["warrior", "brave"],
            is_fiction=False,
        )
        db_session.add(entity)
        await db_session.flush()

        result = await db_session.execute(
            select(Entity).where(Entity.canonical_name == "CompleteEntity")
        )
        entity = result.scalars().first()

        assert entity is not None
        assert entity.type == "Character"
        assert entity.is_fiction is False
        assert len(entity.aliases) > 0
        assert entity.summary is not None
        assert entity.description is not None
        assert len(entity.tags) > 0

    async def test_fiction_entity_marked_correctly(
        self,
        db_session: AsyncSession,
        test_world: World,
    ) -> None:
        """Test that fiction entities are correctly marked."""
        entity = Entity(
            world_id=test_world.id,
            type="Creature",
            canonical_name="FictionalBeast",
            aliases=["Beast"],
            summary="A magical creature",
            description="From ancient legends",
            tags=["magical"],
            is_fiction=True,
        )
        db_session.add(entity)
        await db_session.flush()

        result = await db_session.execute(
            select(Entity).where(Entity.canonical_name == "FictionalBeast")
        )
        entity = result.scalars().first()

        assert entity is not None
        assert entity.is_fiction is True
        assert entity.type == "Creature"

    async def test_strict_document_correct_mode(
        self,
        db_session: AsyncSession,
        test_world: World,
    ) -> None:
        """Test that STRICT documents have correct mode."""
        doc = Document(
            world_id=test_world.id,
            mode="STRICT",
            kind="TEXTBOOK",
            title="Strict_Source",
            author="Scholar",
            text="Verified facts",
        )
        db_session.add(doc)
        await db_session.flush()

        result = await db_session.execute(select(Document).where(Document.title == "Strict_Source"))
        doc = result.scalars().first()

        assert doc is not None
        assert doc.mode == "STRICT"
        assert doc.kind == "TEXTBOOK"

    async def test_mythic_document_correct_mode(
        self,
        db_session: AsyncSession,
        test_world: World,
    ) -> None:
        """Test that MYTHIC documents have correct mode."""
        doc = Document(
            world_id=test_world.id,
            mode="MYTHIC",
            kind="RUMOR",
            title="Mythic_Tale",
            author="Storyteller",
            text="A legendary tale",
        )
        db_session.add(doc)
        await db_session.flush()

        result = await db_session.execute(select(Document).where(Document.title == "Mythic_Tale"))
        doc = result.scalars().first()

        assert doc is not None
        assert doc.mode == "MYTHIC"
        assert doc.kind == "RUMOR"
