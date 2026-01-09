"""
Tests for API error handling and error responses.
"""

from uuid import uuid4

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from lorekeeper.db.models import Entity, World


class TestEntityErrorHandling:
    """Tests for entity endpoint error handling."""

    @pytest.mark.asyncio
    async def test_create_entity_with_invalid_type_returns_400(
        self,
        client: AsyncClient,
        test_world: World,
    ) -> None:
        """Test creating an entity with invalid data returns 400."""
        response = await client.post(
            f"/worlds/{test_world.id}/entities",
            json={
                "type": "",  # Empty type should cause error
                "canonical_name": "Test",
                "aliases": [],
                "summary": "Test",
                "description": "Test",
                "tags": [],
                "is_fiction": False,
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    @pytest.mark.asyncio
    async def test_get_nonexistent_entity_returns_404(
        self,
        client: AsyncClient,
        test_world: World,
    ) -> None:
        """Test getting a non-existent entity returns 404."""
        fake_id = uuid4()
        response = await client.get(f"/worlds/{test_world.id}/entities/{fake_id}")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Entity not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_entity_from_wrong_world_returns_404(
        self,
        client: AsyncClient,
        test_world: World,
        test_entity: Entity,
        db_session: AsyncSession,
    ) -> None:
        """Test getting an entity with mismatched world ID returns 404."""
        # Create another world
        other_world = World(name="OtherWorld", description="Another world")
        db_session.add(other_world)
        await db_session.flush()
        await db_session.refresh(other_world)

        # Try to access test_entity with other_world ID
        response = await client.get(f"/worlds/{other_world.id}/entities/{test_entity.id}")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_update_nonexistent_entity_returns_404(
        self,
        client: AsyncClient,
        test_world: World,
    ) -> None:
        """Test updating a non-existent entity returns 404."""
        fake_id = uuid4()
        response = await client.patch(
            f"/worlds/{test_world.id}/entities/{fake_id}",
            json={"canonical_name": "Updated"},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestWorldErrorHandling:
    """Tests for world endpoint error handling."""

    @pytest.mark.asyncio
    async def test_get_nonexistent_world_returns_404(
        self,
        client: AsyncClient,
    ) -> None:
        """Test getting a non-existent world returns 404."""
        fake_id = uuid4()
        response = await client.get(f"/worlds/{fake_id}")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_create_world_with_empty_name_returns_422(
        self,
        client: AsyncClient,
    ) -> None:
        """Test creating a world with empty name returns 422."""
        response = await client.post(
            "/worlds",
            json={
                "name": "",  # Empty name
                "description": "Test world",
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


class TestDocumentErrorHandling:
    """Tests for document endpoint error handling."""

    @pytest.mark.asyncio
    async def test_get_nonexistent_document_returns_404(
        self,
        client: AsyncClient,
        test_world: World,
    ) -> None:
        """Test getting a non-existent document returns 404."""
        fake_id = uuid4()
        response = await client.get(f"/worlds/{test_world.id}/documents/{fake_id}")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_create_document_with_missing_required_field_returns_422(
        self,
        client: AsyncClient,
        test_world: World,
    ) -> None:
        """Test creating a document without required field returns 422."""
        response = await client.post(
            f"/worlds/{test_world.id}/documents",
            json={
                "mode": "STRICT",
                # Missing required 'kind'
                "title": "Test",
                "author": "Test",
                "text": "Test document content",
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


class TestClaimErrorHandling:
    """Tests for claim endpoint error handling."""

    @pytest.mark.asyncio
    async def test_get_nonexistent_claim_returns_404(
        self,
        client: AsyncClient,
        test_world: World,
    ) -> None:
        """Test getting a non-existent claim returns 404."""
        fake_id = uuid4()
        response = await client.get(f"/worlds/{test_world.id}/claims/{fake_id}")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Claim not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_claim_for_nonexistent_world_returns_404(
        self,
        client: AsyncClient,
    ) -> None:
        """Test creating a claim in a non-existent world returns 404."""
        fake_world_id = uuid4()
        fake_entity_id = uuid4()
        response = await client.post(
            f"/worlds/{fake_world_id}/claims",
            json={
                "subject_entity_id": str(fake_entity_id),
                "predicate": "test_predicate",
                "object_text": "test object",
                "truth_status": "CANON_TRUE",
            },
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestMentionErrorHandling:
    """Tests for mention endpoint error handling."""

    @pytest.mark.asyncio
    async def test_get_nonexistent_mention_returns_404(
        self,
        client: AsyncClient,
        test_world: World,
    ) -> None:
        """Test getting a non-existent mention returns 404."""
        fake_id = uuid4()
        response = await client.get(f"/worlds/{test_world.id}/mentions/{fake_id}")
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestRetrievalErrorHandling:
    """Tests for retrieval endpoint error handling."""

    @pytest.mark.asyncio
    async def test_retrieve_with_query_parameter_required(
        self,
        client: AsyncClient,
        test_world: World,
    ) -> None:
        """Test retrieval requires query parameter."""
        response = await client.post(
            f"/worlds/{test_world.id}/retrieve",
            json={
                # Missing query parameter
                "policy": "HYBRID",
                "limit": 10,
            },
        )
        # Should either require query or handle gracefully
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        ]


class TestValidationErrors:
    """Tests for request validation errors."""

    @pytest.mark.asyncio
    async def test_missing_required_field_returns_422(
        self,
        client: AsyncClient,
        test_world: World,
    ) -> None:
        """Test that missing required field returns 422."""
        response = await client.post(
            f"/worlds/{test_world.id}/entities",
            json={
                # Missing required 'canonical_name'
                "type": "Character",
                "aliases": [],
                "summary": "Test",
                "description": "Test",
                "tags": [],
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    @pytest.mark.asyncio
    async def test_invalid_query_parameter_returns_422(
        self,
        client: AsyncClient,
        test_world: World,
    ) -> None:
        """Test that invalid query parameter returns 422."""
        response = await client.post(
            f"/worlds/{test_world.id}/entities/search",
            params={"limit": -1},  # Invalid: limit must be >= 1
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
