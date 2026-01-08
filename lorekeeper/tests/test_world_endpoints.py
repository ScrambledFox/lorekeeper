"""
Integration tests for World API endpoints.
"""

import pytest
from httpx import AsyncClient

from lorekeeper.db.models import World


class TestWorldEndpoints:
    """Test suite for World endpoints."""

    @pytest.mark.asyncio
    async def test_create_world(self, client: AsyncClient) -> None:
        """Test creating a world."""
        response = await client.post(
            "/worlds",
            json={
                "name": "NewWorld",
                "description": "A new world",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "NewWorld"
        assert data["description"] == "A new world"
        assert "id" in data
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_create_world_without_description(self, client: AsyncClient) -> None:
        """Test creating a world without description."""
        response = await client.post(
            "/worlds",
            json={"name": "SimpleWorld"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "SimpleWorld"
        assert data["description"] is None

    @pytest.mark.asyncio
    async def test_create_world_invalid_name(self, client: AsyncClient) -> None:
        """Test creating a world with invalid name."""
        response = await client.post(
            "/worlds",
            json={
                "name": "",  # Empty name
                "description": "Invalid world",
            },
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_get_world(self, client: AsyncClient, test_world: World) -> None:
        """Test getting a world by ID."""
        response = await client.get(f"/worlds/{test_world.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_world.id)
        assert data["name"] == test_world.name
        assert data["description"] == test_world.description

    @pytest.mark.asyncio
    async def test_get_nonexistent_world(self, client: AsyncClient) -> None:
        """Test getting a non-existent world."""
        from uuid import uuid4

        response = await client.get(f"/worlds/{uuid4()}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_world_timestamps(self, client: AsyncClient, test_world: World) -> None:
        """Test that world has proper timestamps."""
        response = await client.get(f"/worlds/{test_world.id}")

        assert response.status_code == 200
        data = response.json()
        assert "created_at" in data
        assert "updated_at" in data
        assert data["created_at"] == data["updated_at"]
