"""
Integration tests for world creation and management.

This module tests the creation and retrieval of worlds, which are the
foundational containers for all lore in LoreKeeper.
"""

import pytest
from httpx import AsyncClient

from lorekeeper.db.models import World


class TestWorldInitialization:
    """Test suite for initializing and creating new worlds."""

    @pytest.mark.asyncio
    async def test_create_new_world_with_description(self, client: AsyncClient) -> None:
        """Test creating a new campaign world with full details."""
        response = await client.post(
            "/worlds",
            json={
                "name": "The Shattered Realms",
                "description": "A world torn apart by ancient magic and forgotten wars",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "The Shattered Realms"
        assert data["description"] == "A world torn apart by ancient magic and forgotten wars"
        assert "id" in data
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_create_world_with_minimal_information(self, client: AsyncClient) -> None:
        """Test creating a world with only a name."""
        response = await client.post(
            "/worlds",
            json={"name": "Unnamed Realm"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Unnamed Realm"
        assert data["description"] is None

    @pytest.mark.asyncio
    async def test_create_world_requires_valid_name(self, client: AsyncClient) -> None:
        """Test that world creation requires a valid, non-empty name."""
        response = await client.post(
            "/worlds",
            json={
                "name": "",  # Empty name is invalid
                "description": "Invalid world",
            },
        )

        assert response.status_code == 422  # Validation error


class TestWorldRetrieval:
    """Test suite for retrieving world information."""

    @pytest.mark.asyncio
    async def test_retrieve_world_by_id(self, client: AsyncClient, test_world: World) -> None:
        """Test retrieving a world's details by its ID."""
        response = await client.get(f"/worlds/{test_world.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_world.id)
        assert data["name"] == test_world.name
        assert data["description"] == test_world.description

    @pytest.mark.asyncio
    async def test_retrieve_nonexistent_world(self, client: AsyncClient) -> None:
        """Test retrieving a world that does not exist."""
        from uuid import uuid4

        response = await client.get(f"/worlds/{uuid4()}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestWorldMetadata:
    """Test suite for world metadata and versioning."""

    @pytest.mark.asyncio
    async def test_world_creation_timestamps(self, client: AsyncClient, test_world: World) -> None:
        """Test that worlds have proper creation and update timestamps."""
        from datetime import datetime

        response = await client.get(f"/worlds/{test_world.id}")

        assert response.status_code == 200
        data = response.json()
        assert "created_at" in data
        assert "updated_at" in data

        # Parse the timestamps
        created = datetime.fromisoformat(data["created_at"])
        updated = datetime.fromisoformat(data["updated_at"])

        # On creation, both timestamps should be very close (within 1 second)
        # but may differ slightly due to ORM behavior
        time_diff = abs((updated - created).total_seconds())
        assert time_diff < 1.0
