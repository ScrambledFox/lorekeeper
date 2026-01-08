"""
Integration tests for canonical entities (strict lore).

This module tests the creation and management of canonical entities - the
authoritative facts and beings that define the base reality of a world.
"""

import pytest
from httpx import AsyncClient

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
