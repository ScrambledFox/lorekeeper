"""
Integration tests for Entity API endpoints.
"""

import pytest
from httpx import AsyncClient

from lorekeeper.db.models import Entity, World


class TestEntityEndpoints:
    """Test suite for Entity endpoints."""

    @pytest.mark.asyncio
    async def test_create_entity(self, client: AsyncClient, test_world: World) -> None:
        """Test creating an entity."""
        response = await client.post(
            f"/worlds/{test_world.id}/entities",
            json={
                "type": "Character",
                "canonical_name": "Hero",
                "aliases": ["The Hero"],
                "summary": "A brave hero",
                "description": "A hero of great renown",
                "tags": ["warrior", "brave"],
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
    async def test_create_entity_minimal(self, client: AsyncClient, test_world: World) -> None:
        """Test creating an entity with minimal fields."""
        response = await client.post(
            f"/worlds/{test_world.id}/entities",
            json={
                "type": "Location",
                "canonical_name": "Mountain",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["canonical_name"] == "Mountain"
        assert data["type"] == "Location"
        assert data["summary"] is None
        assert data["aliases"] == []

    @pytest.mark.asyncio
    async def test_get_entity(self, client: AsyncClient, test_entity: Entity) -> None:
        """Test getting an entity by ID."""
        response = await client.get(f"/worlds/{test_entity.world_id}/entities/{test_entity.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_entity.id)
        assert data["canonical_name"] == test_entity.canonical_name
        assert data["type"] == test_entity.type

    @pytest.mark.asyncio
    async def test_get_nonexistent_entity(self, client: AsyncClient, test_world: World) -> None:
        """Test getting a non-existent entity."""
        from uuid import uuid4

        response = await client.get(f"/worlds/{test_world.id}/entities/{uuid4()}")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_entity(self, client: AsyncClient, test_entity: Entity) -> None:
        """Test updating an entity."""
        response = await client.patch(
            f"/worlds/{test_entity.world_id}/entities/{test_entity.id}",
            json={
                "summary": "Updated summary",
                "tags": ["warrior", "brave", "legendary"],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["summary"] == "Updated summary"
        assert "legendary" in data["tags"]

    @pytest.mark.asyncio
    async def test_search_entities_by_name(self, client: AsyncClient, test_entity: Entity) -> None:
        """Test searching entities by name."""
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
    async def test_search_entities_no_results(self, client: AsyncClient, test_world: World) -> None:
        """Test searching entities with no results."""
        response = await client.post(
            f"/worlds/{test_world.id}/entities/search",
            json={"query": "NonExistent"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert len(data["results"]) == 0

    @pytest.mark.asyncio
    async def test_search_entities_by_type(self, client: AsyncClient, test_entity: Entity) -> None:
        """Test searching entities by type."""
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
        results_types = [r["type"] for r in data["results"]]
        assert all(t == "Character" for t in results_types)

    @pytest.mark.asyncio
    async def test_search_entities_pagination(
        self, client: AsyncClient, test_entity: Entity
    ) -> None:
        """Test entity search pagination."""
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
