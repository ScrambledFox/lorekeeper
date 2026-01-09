"""
Integration tests for canonical entities (strict lore).

This module tests the creation and management of canonical entities - the
authoritative facts and beings that define the base reality of a world.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from lorekeeper.db.models import Entity, World


class TestCanonicalEntityCreation:
    """Test suite for creating canonical entities."""

    @pytest.mark.asyncio
    async def test_create_character_entity(self, client: AsyncClient, test_world: World) -> None:
        """Test creating a canonical character entity."""
        response = await client.post(
            f"/worlds/{test_world.id}/entities",
            json={
                "type": "Character",
                "canonical_name": "Hero",
                "aliases": ["The Hero", "The Chosen One"],
                "summary": "A brave hero",
                "description": "A hero of great renown who saved the realm",
                "tags": ["warrior", "brave", "legendary"],
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["canonical_name"] == "Hero"
        assert data["type"] == "Character"
        assert "warrior" in data["tags"]
        assert "id" in data
        assert data["world_id"] == str(test_world.id)

    @pytest.mark.asyncio
    async def test_create_minimal_entity(self, client: AsyncClient, test_world: World) -> None:
        """Test creating an entity with only required fields."""
        response = await client.post(
            f"/worlds/{test_world.id}/entities",
            json={
                "type": "Location",
                "canonical_name": "The Shattered Peak",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["canonical_name"] == "The Shattered Peak"
        assert data["type"] == "Location"
        assert data["summary"] is None
        assert data["aliases"] == []


class TestEntityTypes:
    """Test suite for different types of canonical entities."""

    @pytest.mark.asyncio
    async def test_create_faction_entity(self, client: AsyncClient, test_world: World) -> None:
        """Test creating a faction/organization entity."""
        response = await client.post(
            f"/worlds/{test_world.id}/entities",
            json={
                "type": "Faction",
                "canonical_name": "The Order of the Silver Flame",
                "aliases": ["Silver Order", "The Keepers"],
                "summary": "An ancient order of monks",
                "description": "A monastic order dedicated to preserving ancient knowledge",
                "tags": ["monastic", "knowledge-keepers", "neutral"],
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["type"] == "Faction"

    @pytest.mark.asyncio
    async def test_create_location_entity(self, client: AsyncClient, test_world: World) -> None:
        """Test creating a location/place entity."""
        response = await client.post(
            f"/worlds/{test_world.id}/entities",
            json={
                "type": "Location",
                "canonical_name": "The Forgotten Citadel",
                "aliases": ["Citadel of the Ancients"],
                "summary": "A ruined fortress from ages past",
                "description": "Built by the ancients, now a monument to fallen empires",
                "tags": ["ruins", "ancient", "dangerous"],
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["type"] == "Location"


class TestEntityRetrieval:
    """Test suite for retrieving entity information."""

    @pytest.mark.asyncio
    async def test_retrieve_entity_by_id(self, client: AsyncClient, test_entity: Entity) -> None:
        """Test retrieving a canonical entity by its ID."""
        response = await client.get(f"/worlds/{test_entity.world_id}/entities/{test_entity.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_entity.id)
        assert data["canonical_name"] == test_entity.canonical_name
        assert data["type"] == test_entity.type

    @pytest.mark.asyncio
    async def test_retrieve_nonexistent_entity(
        self, client: AsyncClient, test_world: World
    ) -> None:
        """Test retrieving an entity that does not exist."""
        from uuid import uuid4

        response = await client.get(f"/worlds/{test_world.id}/entities/{uuid4()}")

        assert response.status_code == 404


class TestEntityUpdates:
    """Test suite for updating canonical entity information."""

    @pytest.mark.asyncio
    async def test_update_entity_information(
        self, client: AsyncClient, test_entity: Entity
    ) -> None:
        """Test updating an entity's canonical information."""
        response = await client.patch(
            f"/worlds/{test_entity.world_id}/entities/{test_entity.id}",
            json={
                "summary": "An even more legendary hero",
                "tags": ["warrior", "brave", "legendary", "immortal"],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["summary"] == "An even more legendary hero"
        assert "immortal" in data["tags"]


class TestEntityDiscovery:
    """Test suite for searching and discovering entities."""

    @pytest.mark.asyncio
    async def test_find_entity_by_canonical_name(
        self, client: AsyncClient, test_entity: Entity
    ) -> None:
        """Test finding an entity by its canonical name."""
        response = await client.post(
            f"/worlds/{test_entity.world_id}/entities/search",
            json={"query": "TestHero"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert len(data["results"]) >= 1
        assert data["results"][0]["canonical_name"] == "TestHero"

    @pytest.mark.asyncio
    async def test_search_returns_no_results_for_nonexistent_entity(
        self, client: AsyncClient, test_world: World
    ) -> None:
        """Test that searching for non-existent entities returns empty results."""
        response = await client.post(
            f"/worlds/{test_world.id}/entities/search",
            json={"query": "NeverExisted"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert len(data["results"]) == 0

    @pytest.mark.asyncio
    async def test_filter_entities_by_type(self, client: AsyncClient, test_entity: Entity) -> None:
        """Test filtering entities by their type."""
        response = await client.post(
            f"/worlds/{test_entity.world_id}/entities/search",
            json={
                "query": "Test",
                "entity_type": "Character",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        # All results should be of the requested type
        results_types = [r["type"] for r in data["results"]]
        assert all(t == "Character" for t in results_types)

    @pytest.mark.asyncio
    async def test_entity_search_pagination(self, client: AsyncClient, test_entity: Entity) -> None:
        """Test paginating through entity search results."""
        response = await client.post(
            f"/worlds/{test_entity.world_id}/entities/search",
            json={
                "query": "Test",
                "limit": 5,
                "offset": 0,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) <= 5


class TestEnhancedEntitySearch:
    """Test suite for enhanced entity search across multiple fields."""

    @pytest.mark.asyncio
    async def test_search_by_alias(
        self,
        client: AsyncClient,
        test_world: World,
        db_session: AsyncSession,
        override_get_session: bool,
    ) -> None:
        """Test searching entities by their aliases."""
        from lorekeeper.db.models import Entity

        # Create entity with aliases
        entity = Entity(
            world_id=test_world.id,
            type="Character",
            canonical_name="Aldren the Wise",
            aliases=["Arch-Mage Aldren", "The Silver Sage"],
            summary="A legendary wizard",
        )
        db_session.add(entity)
        await db_session.flush()

        # Test 1: Search by full alias
        response = await client.post(
            f"/worlds/{test_world.id}/entities/search",
            json={"query": "Silver Sage"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert any(e["canonical_name"] == "Aldren the Wise" for e in data["results"])

        # Test 2: Search by partial alias (just "Silver")
        response = await client.post(
            f"/worlds/{test_world.id}/entities/search",
            json={"query": "Silver"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert any(e["canonical_name"] == "Aldren the Wise" for e in data["results"])

        # Test 3: Search by another alias partial
        response = await client.post(
            f"/worlds/{test_world.id}/entities/search",
            json={"query": "Arch-Mage"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert any(e["canonical_name"] == "Aldren the Wise" for e in data["results"])

    @pytest.mark.asyncio
    async def test_search_by_summary(
        self,
        client: AsyncClient,
        test_world: World,
        db_session: AsyncSession,
        override_get_session: bool,
    ) -> None:
        """Test searching entities by their summary field."""
        from lorekeeper.db.models import Entity

        # Create entity with descriptive summary
        entity = Entity(
            world_id=test_world.id,
            type="Faction",
            canonical_name="Order of the Black Tower",
            summary="A secret society of necromancers plotting world domination",
        )
        db_session.add(entity)
        await db_session.flush()

        # Search by summary keyword
        response = await client.post(
            f"/worlds/{test_world.id}/entities/search",
            json={"query": "necromancers"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert any(e["canonical_name"] == "Order of the Black Tower" for e in data["results"])

    @pytest.mark.asyncio
    async def test_search_by_description(
        self,
        client: AsyncClient,
        test_world: World,
        db_session: AsyncSession,
        override_get_session: bool,
    ) -> None:
        """Test searching entities by their description field."""
        from lorekeeper.db.models import Entity

        # Create entity with detailed description
        entity = Entity(
            world_id=test_world.id,
            type="Location",
            canonical_name="The Shattered Citadel",
            summary="Ruins of an ancient fortress",
            description="The Shattered Citadel stands atop Mount Desolation, a monument to the last great kingdom. Its towers crumble from centuries of siege and abandonment. Within its walls, legends say, lies treasure beyond measure.",
        )
        db_session.add(entity)
        await db_session.flush()

        # Search by description keyword
        response = await client.post(
            f"/worlds/{test_world.id}/entities/search",
            json={"query": "Mount Desolation"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert any(e["canonical_name"] == "The Shattered Citadel" for e in data["results"])

    @pytest.mark.asyncio
    async def test_search_cross_field_matching(
        self,
        client: AsyncClient,
        test_world: World,
        db_session: AsyncSession,
        override_get_session: bool,
    ) -> None:
        """Test that search returns results from multiple field matches."""
        from lorekeeper.db.models import Entity

        # Create multiple entities with the search term in different fields
        entity1 = Entity(
            world_id=test_world.id,
            type="Character",
            canonical_name="Dragon Lord",
            summary="Peaceful sage",
        )
        entity2 = Entity(
            world_id=test_world.id,
            type="Location",
            canonical_name="Dragon's Peak",
            summary="A mountain",
        )
        entity3 = Entity(
            world_id=test_world.id,
            type="Artifact",
            canonical_name="Ancient Sword",
            description="A legendary blade forged in dragon fire",
        )
        db_session.add_all([entity1, entity2, entity3])
        await db_session.flush()

        # Search for "dragon"
        response = await client.post(
            f"/worlds/{test_world.id}/entities/search",
            json={"query": "dragon"},
        )

        assert response.status_code == 200
        data = response.json()
        # Should find all three entities
        assert data["total"] >= 3
        names = {e["canonical_name"] for e in data["results"]}
        assert "Dragon Lord" in names
        assert "Dragon's Peak" in names
        assert "Ancient Sword" in names

    @pytest.mark.asyncio
    async def test_search_case_insensitive(
        self,
        client: AsyncClient,
        test_world: World,
        db_session: AsyncSession,
        override_get_session: bool,
    ) -> None:
        """Test that search is case-insensitive across all fields."""
        from lorekeeper.db.models import Entity

        entity = Entity(
            world_id=test_world.id,
            type="Character",
            canonical_name="Phoenix Rising",
            summary="A majestic firebird reborn from ashes",
        )
        db_session.add(entity)
        await db_session.flush()

        # Search with different case
        response = await client.post(
            f"/worlds/{test_world.id}/entities/search",
            json={"query": "FIREBIRD"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert any(e["canonical_name"] == "Phoenix Rising" for e in data["results"])

    @pytest.mark.asyncio
    async def test_search_partial_word_match(
        self,
        client: AsyncClient,
        test_world: World,
        db_session: AsyncSession,
        override_get_session: bool,
    ) -> None:
        """Test that search matches partial words."""
        from lorekeeper.db.models import Entity

        entity = Entity(
            world_id=test_world.id,
            type="Character",
            canonical_name="Elara Moonwhisper",
            summary="An elven ranger of the moonlit woods",
        )
        db_session.add(entity)
        await db_session.flush()

        # Search for partial word
        response = await client.post(
            f"/worlds/{test_world.id}/entities/search",
            json={"query": "moon"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert any(e["canonical_name"] == "Elara Moonwhisper" for e in data["results"])

    @pytest.mark.asyncio
    async def test_search_combined_with_type_filter(
        self,
        client: AsyncClient,
        test_world: World,
        db_session: AsyncSession,
        override_get_session: bool,
    ) -> None:
        """Test that search query works with type filtering."""
        from lorekeeper.db.models import Entity

        # Create a unique character with a unique name
        char = Entity(
            world_id=test_world.id,
            type="Character",
            canonical_name="Unique Wizard Aldaron",
            summary="A wizard of exceptional skill",
        )
        db_session.add(char)
        await db_session.flush()

        # Search for unique name with type filter
        response = await client.post(
            f"/worlds/{test_world.id}/entities/search",
            json={
                "query": "Aldaron",
                "entity_type": "Character",
            },
        )

        assert response.status_code == 200
        data = response.json()
        # All results should be Character type
        assert all(e["type"] == "Character" for e in data["results"])
        # Should find our unique character
        assert any(e["canonical_name"] == "Unique Wizard Aldaron" for e in data["results"])


class TestEntityFictionStatus:
    """Test suite for distinguishing between Fact and Fiction entities."""

    @pytest.mark.asyncio
    async def test_create_fact_entity(self, client: AsyncClient, test_world: World) -> None:
        """Test creating a fact entity (is_fiction=False)."""
        response = await client.post(
            f"/worlds/{test_world.id}/entities",
            json={
                "type": "Character",
                "canonical_name": "King Aldren",
                "summary": "A historical ruler",
                "is_fiction": False,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["canonical_name"] == "King Aldren"
        assert data["is_fiction"] is False

    @pytest.mark.asyncio
    async def test_create_fiction_entity(self, client: AsyncClient, test_world: World) -> None:
        """Test creating a fiction entity (is_fiction=True)."""
        response = await client.post(
            f"/worlds/{test_world.id}/entities",
            json={
                "type": "Creature",
                "canonical_name": "Scibble",
                "summary": "A whimsical in-lore fantasy creature",
                "is_fiction": True,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["canonical_name"] == "Scibble"
        assert data["is_fiction"] is True

    @pytest.mark.asyncio
    async def test_create_entity_defaults_to_fact(
        self, client: AsyncClient, test_world: World
    ) -> None:
        """Test that entities default to is_fiction=False if not specified."""
        response = await client.post(
            f"/worlds/{test_world.id}/entities",
            json={
                "type": "Location",
                "canonical_name": "Lake Silvermere",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["is_fiction"] is False

    @pytest.mark.asyncio
    async def test_update_entity_fiction_status(
        self, client: AsyncClient, test_entity: Entity
    ) -> None:
        """Test updating an entity's fiction status."""
        response = await client.patch(
            f"/worlds/{test_entity.world_id}/entities/{test_entity.id}",
            json={
                "is_fiction": True,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_fiction"] is True

    @pytest.mark.asyncio
    async def test_retrieve_entity_includes_fiction_status(
        self, client: AsyncClient, test_entity: Entity
    ) -> None:
        """Test that retrieved entities include is_fiction field."""
        response = await client.get(f"/worlds/{test_entity.world_id}/entities/{test_entity.id}")

        assert response.status_code == 200
        data = response.json()
        assert "is_fiction" in data
        assert isinstance(data["is_fiction"], bool)
